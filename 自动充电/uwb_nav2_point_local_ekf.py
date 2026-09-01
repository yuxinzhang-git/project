#!/usr/bin/env python3
"""
uwb_nav2_point_local_ekf.py - UWB处理流水线 + EKF滤波 + Nav2 NavigateToPose 单点导航
====================================================================================
在 uwb_nav2_point_local.py 基础上, 中值滤波后增加一个2D匀速EKF。

  串口UWB → 滤波 → 面包屑 → 回退合并(去迂回) → 截断(从机器人位置)
  → 取最后一个点(信标位置) → NavigateToPose Goal → Nav2 控制器

处理流水线:
  原始帧 → 方位角中值滤波 → AoA漂移检测 → 跳变滤波
  → TF变换(local系) → 中值滤波 → ★ EKF(匀速模型) → 面包屑队列
  → 回退合并(去迂回) → 截断(机器人前方)
  → 取 trimmed[-1] → NavigateToPose (send_goal_async)

EKF 状态:  [x, y, vx, vy]   (位置 + 速度, local系)
EKF 观测:  [x, y]             (中值滤波输出)
EKF 模型:  匀速 (CV), dt由帧间隔自适应

话题:
  /uwb/raw_point_local     — local 系原始坐标
  /uwb/filtered_point      — local 系中值滤波后坐标
  /uwb/ekf_point           — local 系 EKF 滤波后坐标 ★ 新增
  /uwb/beacon_point        — local 系最终信标目标点 (发给 Nav2 的点)
  /uwb/filtered_path       — local 系原面包屑路径
  /uwb/optimized_path      — local 系去迂回后优化路径
  /uwb/trimmed_path        — local 系截断后规划路径

Action Client:
  navigate_to_pose (nav2_msgs/NavigateToPose) → Nav2 导航栈
  坐标系: local

用法: ros2 run <package> uwb_nav2_point_local_ekf.py
"""

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.duration import Duration
from rclpy.action import ActionClient

import serial
import math
import time as time_mod
import numpy as np
import threading
import queue as Queue

from geometry_msgs.msg import PointStamped, PoseStamped
from nav_msgs.msg import Path
from builtin_interfaces.msg import Time as TimeMsg
from nav2_msgs.action import NavigateToPose

from tf2_ros import Buffer, TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException


# ============================================================
# 硬编码参数
# ============================================================
SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200
TIMEOUT = 1
FRAME_HEADER = b'\xFF\xFF\xFF\xFF'
CMD_POSITION = 0x2001
FRAME_LEN_POSITION = 37
ANTENNA_OFFSET = 0.4

# -- 帧间跳变滤波 --
MAX_DIS_JUMP = 3
MAX_AZI_JUMP = 90

# -- AoA漂移检测 --
DRIFT_WINDOW = 7
DRIFT_DIS_STABLE = 0.3
DRIFT_AZI_SPREAD = 30

# -- 中值滤波 --
MEDIAN_WINDOW = 7
MEDIAN_AZI_WINDOW = 5

# -- EKF 参数 --
EKF_PROCESS_NOISE_POS = 0.05    # 位置过程噪声标准差 (m)
EKF_PROCESS_NOISE_VEL = 0.5     # 速度过程噪声标准差 (m/s)
EKF_MEASURE_NOISE = 0.15        # 观测噪声标准差 (m) — UWB中值滤波后典型精度
EKF_INIT_VEL_STD = 1.0          # 初始速度不确定度 (m/s)
EKF_MIN_DT = 0.01               # 最小dt, 防止除零

# -- 面包屑 --
BREADCRUMB_DIST = 0.5
BREADCRUMB_MAX_SIZE = 100
PUBLISH_INTERVAL = 3.0

# -- 面包屑回退合并 --
BACKTRACK_SPATIAL_THRESHOLD = 0.5
BACKTRACK_DETOUR_RATIO = 2.5
BACKTRACK_MAX_SEARCH_AHEAD = 0
BACKTRACK_MAX_ITERATIONS = 10

# -- 路径截断 --
TRIM_MIN_TRAIL_POINTS = 2

# -- Nav2 NavigateToPose 控制器 --
NAV2_ACTION_NAME = 'navigate_to_pose'
NAV2_GOAL_FRAME = 'local'
NAV2_DEAD_ZONE_DIST = 0.8
NAV2_MIN_MOVE_DIST = 0.15

# -- TF 坐标系 --
LOCAL_FRAME = 'local'
BASE_FRAME = 'base_link'

# -- 多线程 --
QUEUE_MAXSIZE = 20
QUEUE_GET_TIMEOUT = 0.5
BUFFER_MAX = 200

# -- 处理循环 --
PROCESSING_RATE = 20

# -- 路径可视化降采样 --
PATH_VIZ_MAX_POINTS = 30
PATH_VIZ_MIN_DIST = 0.5  # 发布路径点之间的最小距离 (m), 防止密集点炸Rviz


# ============================================================
# 辅助: 节流日志
# ============================================================
class Throttle:
    def __init__(self, interval=5.0):
        self.interval = interval
        self.last_time = {}

    def should_log(self, key):
        now = time_mod.time()
        if key not in self.last_time:
            self.last_time[key] = now
            return True
        if now - self.last_time[key] >= self.interval:
            self.last_time[key] = now
            return True
        return False


# ============================================================
# 工具函数
# ============================================================
def calc_xor(data):
    xor_sum = 0
    for b in data[:-1]:
        xor_sum ^= b
    return xor_sum


def parse_position(data):
    return {
        "distance":  int.from_bytes(data[20:24], 'big', signed=False),
        "azimuth":   int.from_bytes(data[24:26], 'big', signed=False),
        "elevation": int.from_bytes(data[26:28], 'big', signed=True)
    }


def is_invalid(dis, azi, ele):
    return dis < 0 or azi < 0 or azi > 360


def sec_to_time_msg(t):
    msg = TimeMsg()
    msg.sec = int(t)
    msg.nanosec = int((t - int(t)) * 1e9)
    return msg


# ============================================================
# ★ EKF 2D 匀速模型滤波器
# ============================================================
class EKF2D:
    """
    2D 扩展卡尔曼滤波器 (匀速CV模型)

    状态向量:  x = [px, py, vx, vy]^T
    观测向量:  z = [mx, my]^T   (中值滤波后的local坐标)
    """

    def __init__(self,
                 process_noise_pos=EKF_PROCESS_NOISE_POS,
                 process_noise_vel=EKF_PROCESS_NOISE_VEL,
                 measure_noise=EKF_MEASURE_NOISE,
                 init_vel_std=EKF_INIT_VEL_STD):
        # 状态: [px, py, vx, vy]
        self.x = np.zeros((4, 1))
        self.P = np.eye(4) * 0.01           # 初始位置不确定度小
        self.P[2, 2] = init_vel_std ** 2    # 速度不确定度大
        self.P[3, 3] = init_vel_std ** 2

        # 观测矩阵 (线性)
        self.H = np.array([[1, 0, 0, 0],
                           [0, 1, 0, 0]], dtype=np.float64)

        # 观测噪声协方差
        self.R = np.eye(2) * (measure_noise ** 2)

        # 过程噪声基础参数
        self.q_pos = process_noise_pos
        self.q_vel = process_noise_vel

        # 状态管理
        self.initialized = False
        self.last_time = None                 # 上一帧 time_mod.time()
        self.convergence_counter = 0          # 收敛计数

    def predict(self, dt):
        """匀速模型预测: x_k = F * x_{k-1} + w"""
        dt = max(dt, EKF_MIN_DT)

        # 状态转移矩阵
        F = np.array([[1, 0, dt, 0],
                      [0, 1, 0, dt],
                      [0, 0, 1,  0],
                      [0, 0, 0,  1]], dtype=np.float64)

        # 过程噪声协方差 (离散化, 从连续白噪声推导)
        # Q_discrete = G * Q_cont * G^T, G = [dt^2/2 * I, dt * I]^T
        dt2 = 0.5 * dt * dt
        G = np.array([[dt2, 0],
                      [0,   dt2],
                      [dt,  0],
                      [0,   dt]], dtype=np.float64)
        Q_cont = np.diag([self.q_pos ** 2, self.q_pos ** 2])
        Q = G @ Q_cont @ G.T

        # 对速度分量额外加噪声
        vel_noise = (self.q_vel * dt) ** 2
        Q[2, 2] += vel_noise
        Q[3, 3] += vel_noise

        # 预测
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

    def update(self, z):
        """标准 Kalman 更新: z = [mx, my]"""
        z_vec = np.array(z, dtype=np.float64).reshape(2, 1)

        # 创新
        y = z_vec - self.H @ self.x           # 残差
        S = self.H @ self.P @ self.H.T + self.R  # 创新协方差
        K = self.P @ self.H.T @ np.linalg.inv(S) # 卡尔曼增益

        # 更新
        self.x = self.x + K @ y
        self.P = (np.eye(4) - K @ self.H) @ self.P

    def step(self, mx, my, stamp):
        """
        一次完整的 EKF 预测+更新周期。

        参数:
            mx, my:  中值滤波后的观测位置 (local系)
            stamp:   帧时间戳 (time_mod.time())

        返回:
            (ekf_x, ekf_y, ekf_vx, ekf_vy, converged)
        """
        # 初始化: 直接用第一帧位置, 速度=0
        if not self.initialized:
            self.x[0, 0] = mx
            self.x[1, 0] = my
            self.x[2, 0] = 0.0
            self.x[3, 0] = 0.0
            self.last_time = stamp
            self.initialized = True
            self.convergence_counter = 0
            return mx, my, 0.0, 0.0, False

        # 计算 dt
        dt = stamp - self.last_time
        self.last_time = stamp

        # EKF 预测 + 更新
        self.predict(dt)
        self.update([mx, my])

        # 收敛判断: 速度协方差小于阈值认为收敛
        self.convergence_counter += 1
        vel_cov = max(self.P[2, 2], self.P[3, 3])
        converged = vel_cov < 0.5 and self.convergence_counter > 5

        ekf_x = float(self.x[0, 0])
        ekf_y = float(self.x[1, 0])
        ekf_vx = float(self.x[2, 0])
        ekf_vy = float(self.x[3, 0])

        return ekf_x, ekf_y, ekf_vx, ekf_vy, converged

    def reset(self):
        """重置滤波器 (漂移检测触发时调用)"""
        self.x = np.zeros((4, 1))
        self.P = np.eye(4) * 0.01
        self.P[2, 2] = EKF_INIT_VEL_STD ** 2
        self.P[3, 3] = EKF_INIT_VEL_STD ** 2
        self.initialized = False
        self.last_time = None
        self.convergence_counter = 0


# ============================================================
# 面包屑回退检测与合并
# ============================================================
def remove_backtrack_loops(breadcrumbs,
                           spatial_threshold=BACKTRACK_SPATIAL_THRESHOLD,
                           detour_ratio=BACKTRACK_DETOUR_RATIO,
                           max_search_ahead=BACKTRACK_MAX_SEARCH_AHEAD,
                           max_iterations=BACKTRACK_MAX_ITERATIONS):
    """正向贪心扫描, 检测并删除迂回段, 迭代直到收敛 (有安全上限)。"""
    if len(breadcrumbs) < 3:
        return list(breadcrumbs)

    points = list(breadcrumbs)

    def build_cum_len(pts):
        cl = [0.0] * len(pts)
        for i in range(1, len(pts)):
            seg = math.hypot(pts[i][0] - pts[i-1][0],
                             pts[i][1] - pts[i-1][1])
            cl[i] = cl[i-1] + seg
        return cl

    cum_len = build_cum_len(points)

    def path_len_between(i, j):
        return cum_len[j] - cum_len[i]

    iteration = 0
    converged = False
    while not converged and iteration < max_iterations:
        iteration += 1
        converged = True
        n = len(points)
        cum_len = build_cum_len(points)

        new_indices = [0]
        i = 0

        while i < n - 1:
            best_j = i + 1
            best_saved = 0

            search_end = n
            if max_search_ahead > 0:
                search_end = min(i + max_search_ahead + 1, n)

            for j in range(i + 2, search_end):
                dx = points[i][0] - points[j][0]
                dy = points[i][1] - points[j][1]
                d = math.hypot(dx, dy)

                if d < spatial_threshold:
                    path_len = path_len_between(i, j)
                    direct = max(d, 0.01)

                    if path_len / direct > detour_ratio:
                        saved = j - i - 1
                        if saved > best_saved:
                            best_saved = saved
                            best_j = j
                            converged = False

            new_indices.append(best_j)
            i = best_j

        points = [points[idx] for idx in new_indices]

    return points


# ============================================================
# 路径截断
# ============================================================
def trim_from_robot(robot_pos, breadcrumbs,
                    min_trail_points=TRIM_MIN_TRAIL_POINTS,
                    throttle=None, logger=None):
    """找到离机器人最近的面包屑点, 该点之前全部丢弃。"""
    if len(breadcrumbs) <= min_trail_points:
        return list(breadcrumbs)

    rx, ry = robot_pos

    closest_idx = 0
    closest_dist = float('inf')
    for i, (bx, by, _) in enumerate(breadcrumbs):
        d = math.hypot(rx - bx, ry - by)
        if d < closest_dist:
            closest_dist = d
            closest_idx = i

    trimmed = breadcrumbs[closest_idx:]

    if len(trimmed) < min_trail_points:
        if throttle and throttle.should_log('trim_short'):
            logger.warn(
                "[截断] 截断后仅剩 %d 个点 (阈值=%d), 放弃截断, 保留原队列" %
                (len(trimmed), min_trail_points))
        return list(breadcrumbs)

    return trimmed


# ============================================================
# 滑窗中值滤波器
# ============================================================
class SlidingMedian:
    def __init__(self, window=5):
        self.window = max(3, window)
        if self.window % 2 == 0:
            self.window += 1
        self.buf_x = []
        self.buf_y = []

    def filter(self, x, y):
        self.buf_x.append(x)
        self.buf_y.append(y)
        if len(self.buf_x) > self.window:
            self.buf_x.pop(0)
            self.buf_y.pop(0)
        return float(np.median(self.buf_x)), float(np.median(self.buf_y))


# ============================================================
# 方位角中值滤波器
# ============================================================
class SlidingMedianAngle:
    def __init__(self, window=5):
        self.window = max(3, window)
        if self.window % 2 == 0:
            self.window += 1
        self.buf_sin = []
        self.buf_cos = []

    def filter(self, angle_deg):
        rad = math.radians(angle_deg)
        self.buf_sin.append(math.sin(rad))
        self.buf_cos.append(math.cos(rad))
        if len(self.buf_sin) > self.window:
            self.buf_sin.pop(0)
            self.buf_cos.pop(0)
        avg_rad = math.atan2(
            float(np.median(self.buf_sin)),
            float(np.median(self.buf_cos)))
        return math.degrees(avg_rad) % 360


# ============================================================
# AoA 漂移检测器
# ============================================================
class AzimuthDriftDetector:
    def __init__(self, window=7, dis_stable=0.3, azi_spread=30):
        self.window = max(3, window)
        self.dis_stable = dis_stable
        self.azi_spread = azi_spread
        self.buf = []

    def check(self, dis, azi):
        self.buf.append((dis, azi))
        if len(self.buf) > self.window:
            self.buf.pop(0)

        if len(self.buf) < self.window:
            return False

        dis_min = min(d[0] for d in self.buf)
        dis_max = max(d[0] for d in self.buf)
        if dis_max - dis_min > self.dis_stable:
            return False

        azis = sorted(d[1] for d in self.buf)
        max_gap = 0
        for i in range(len(azis) - 1):
            gap = azis[i + 1] - azis[i]
            if gap > max_gap:
                max_gap = gap
        wrap_gap = azis[0] + 360 - azis[-1]
        if wrap_gap > max_gap:
            max_gap = wrap_gap

        spread = 360 - max_gap

        if spread > self.azi_spread:
            self.buf = []
            return True

        return False


# ============================================================
# 串口读取线程
# ============================================================
class UwbSerialReader(threading.Thread):
    def __init__(self, port, baudrate, timeout, queue, stop_event,
                 azi_filter, log_func, err_func):
        super(UwbSerialReader, self).__init__()
        self.daemon = True
        self.name = 'UwbSerialReader'
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.queue = queue
        self.stop_event = stop_event
        self.azi_filter = azi_filter
        self.log = log_func
        self.err = err_func
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(
                port=self.port, baudrate=self.baudrate,
                bytesize=8, parity='N', stopbits=1,
                timeout=self.timeout)
            self.log("[SerialReader] 串口打开成功")
        except Exception as e:
            self.err("[SerialReader] 串口打开失败: %s" % str(e))
            self.stop_event.set()
            return

        buffer_ = bytearray()
        last_heartbeat = time_mod.time()

        # ★ 只用 stop_event 控制循环, 不依赖 rclpy.ok() (子线程中不可靠)
        while not self.stop_event.is_set():
            try:
                data = self.ser.read(64)
                if data:
                    buffer_.extend(data)
                    if len(buffer_) > BUFFER_MAX:
                        buffer_ = buffer_[-BUFFER_MAX:]
            except serial.SerialException as e:
                self.err("[SerialReader] 串口错误: %s" % str(e))
                break
            except Exception as e:
                self.err("[SerialReader] 未知错误: %s" % str(e))
                break

            self._parse_frames(buffer_)

            # 心跳: 每5秒打印一次, 证明线程还在运行
            now = time_mod.time()
            if now - last_heartbeat > 5.0:
                self.log("[SerialReader] 心跳: buf=%d bytes queue≈%d" %
                         (len(buffer_), self.queue.qsize()))
                last_heartbeat = now

        if self.ser and self.ser.is_open:
            self.ser.close()
            self.log("[SerialReader] 串口已关闭")

    def _parse_frames(self, buf):
        while not self.stop_event.is_set():
            idx = buf.find(FRAME_HEADER)
            if idx == -1:
                if len(buf) >= 3:
                    del buf[:-3]
                else:
                    buf.clear()
                break
            if idx > 0:
                del buf[:idx]

            if len(buf) < 6:
                break
            frame_len = int.from_bytes(buf[4:6], 'big')
            if len(buf) < frame_len:
                break

            frame = bytes(buf[:frame_len])
            del buf[:frame_len]

            if calc_xor(frame) != frame[-1]:
                continue

            cmd = int.from_bytes(frame[8:10], 'big')
            if cmd != CMD_POSITION or frame_len != FRAME_LEN_POSITION:
                continue

            res = parse_position(frame)
            raw_dis = res['distance'] / 100.0 - ANTENNA_OFFSET
            raw_azi_orig = float(res['azimuth'])
            raw_ele = float(res['elevation'])

            if is_invalid(raw_dis, raw_azi_orig, raw_ele):
                continue

            raw_azi = self.azi_filter.filter(raw_azi_orig)

            angle_rad = math.radians(raw_azi)
            raw_x = raw_dis * math.cos(angle_rad)
            raw_y = -raw_dis * math.sin(angle_rad)

            item = {
                'stamp':     time_mod.time(),
                'raw_dis':   raw_dis,
                'raw_azi':   raw_azi,
                'raw_x':     raw_x,
                'raw_y':     raw_y,
            }
            self._enqueue_with_eviction(item)

    def _enqueue_with_eviction(self, item):
        while True:
            try:
                self.queue.put_nowait(item)
                return
            except Queue.Full:
                try:
                    self.queue.get_nowait()
                except Queue.Empty:
                    pass


# ============================================================
# 主节点: UWB 处理 + EKF + Nav2 NavigateToPose 单点导航
# ============================================================
class UwbNav2PointEkfNode(Node):
    def __init__(self):
        super().__init__('uwb_nav2_point_ekf')

        # ============ 发布器 ============
        self.pub_local_raw = self.create_publisher(PointStamped, '/uwb/raw_point_local', 10)
        self.pub_local_filt = self.create_publisher(PointStamped, '/uwb/filtered_point', 10)
        self.pub_ekf = self.create_publisher(PointStamped, '/uwb/ekf_point', 10)
        self.pub_beacon = self.create_publisher(PointStamped, '/uwb/beacon_point', 10)
        self.pub_path = self.create_publisher(Path, '/uwb/filtered_path', 1)
        self.pub_opt_path = self.create_publisher(Path, '/uwb/optimized_path', 1)
        self.pub_trim_path = self.create_publisher(Path, '/uwb/trimmed_path', 1)

        # ============ TF2 ============
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # ============ Nav2 NavigateToPose Action Client ============
        self.action_client = ActionClient(self, NavigateToPose, NAV2_ACTION_NAME)
        self.last_goal_x = 0.0
        self.last_goal_y = 0.0

        # ============ 滤波器 ============
        self.median = SlidingMedian(window=MEDIAN_WINDOW)
        self.drift_detector = AzimuthDriftDetector(
            window=DRIFT_WINDOW,
            dis_stable=DRIFT_DIS_STABLE,
            azi_spread=DRIFT_AZI_SPREAD)
        self.ekf = EKF2D()

        # ============ 节流器 ============
        self.throttle = Throttle(interval=5.0)

        # ============ 状态变量 ============
        self.breadcrumb = []
        self.last_bc_point = None
        self.last_raw_dis = None
        self.last_raw_azi = None
        self.last_publish_time = 0.0

        # ============ 统计 ============
        self.stats = {
            'consumed': 0,
            'skipped': 0,
            'drift_skipped': 0,
            'robot_tf_fail': 0,
            'goals_sent': 0,
            'goals_skipped': 0,
        }

        # ============ 多线程: 串口读取 ============
        self.frame_queue = Queue.Queue(maxsize=QUEUE_MAXSIZE)
        self.stop_event = threading.Event()

        self.reader = UwbSerialReader(
            port=SERIAL_PORT, baudrate=BAUDRATE, timeout=TIMEOUT,
            queue=self.frame_queue, stop_event=self.stop_event,
            azi_filter=SlidingMedianAngle(window=MEDIAN_AZI_WINDOW),
            log_func=lambda msg: self.get_logger().info(msg),
            err_func=lambda msg: self.get_logger().error(msg))

        # ============ 打印参数 ============
        self.get_logger().info(
            "[uwb_nav2_point_ekf] UWB处理 + EKF + Nav2 NavigateToPose 单点导航 已启动 "
            "(local坐标系)")
        self.get_logger().info(
            "  中值滤波: delta_dis>%.2fm | delta_azi>%.0f deg" %
            (MAX_DIS_JUMP, MAX_AZI_JUMP))
        self.get_logger().info(
            "  漂移检测: window=%d | dis_stable<%.2fm | azi_spread>%.0f deg" %
            (DRIFT_WINDOW, DRIFT_DIS_STABLE, DRIFT_AZI_SPREAD))
        self.get_logger().info(
            "  EKF: CV模型 | q_pos=%.3f q_vel=%.3f r_meas=%.3f" %
            (EKF_PROCESS_NOISE_POS, EKF_PROCESS_NOISE_VEL, EKF_MEASURE_NOISE))
        self.get_logger().info(
            "  回退合并: spatial_threshold=%.1fm | detour_ratio=%.1f" %
            (BACKTRACK_SPATIAL_THRESHOLD, BACKTRACK_DETOUR_RATIO))
        self.get_logger().info(
            "  路径截断: min_trail_points=%d" % TRIM_MIN_TRAIL_POINTS)
        self.get_logger().info(
            "  发布间隔: %.1f 秒 | 处理频率: %d Hz" %
            (PUBLISH_INTERVAL, PROCESSING_RATE))
        self.get_logger().info(
            "  TF变换: %s -> %s" % (BASE_FRAME, LOCAL_FRAME))
        self.get_logger().info(
            "  Nav2导航: action=%s | frame=%s" %
            (NAV2_ACTION_NAME, NAV2_GOAL_FRAME))
        self.get_logger().info(
            "  目标保护: dead_zone=%.2fm | min_move=%.2fm" %
            (NAV2_DEAD_ZONE_DIST, NAV2_MIN_MOVE_DIST))

        # ============ 启动串口线程 ============
        self.reader.start()
        time_mod.sleep(0.2)
        if not self.reader.is_alive():
            self.get_logger().error("[主线程] 串口线程未能启动, 退出")
            raise RuntimeError("Serial thread failed to start")

        # ============ 处理定时器 ============
        self.processing_timer = self.create_timer(
            1.0 / PROCESSING_RATE, self.processing_callback)

    # ============================================================
    # TF变换: base_link -> local (始终取最新TF)
    # ============================================================
    def transform_to_local(self, frame_item):
        """TF变换: base_link → local (取最新TF, 同ROS1 rospy.Time(0) 语义)"""
        pt_bl = PointStamped()
        pt_bl.header.frame_id = BASE_FRAME
        # ★ ROS2: Time() (seconds=0, ns=0) 等效于 ROS1 rospy.Time(0) = "最新可用TF"
        pt_bl.header.stamp = Time().to_msg()
        pt_bl.point.x = frame_item['raw_x']
        pt_bl.point.y = frame_item['raw_y']
        pt_bl.point.z = 0.0

        try:
            transform = self.tf_buffer.lookup_transform(
                LOCAL_FRAME, BASE_FRAME,
                time=Time(),                    # 最新TF
                timeout=Duration(seconds=0.5)   # 等最多0.5s
            )
            pt_bl.header.stamp = transform.header.stamp
            pt_local = self.tf_buffer.transform(pt_bl, LOCAL_FRAME)
            return pt_local
        except (LookupException, ConnectivityException,
                ExtrapolationException) as e:
            if self.throttle.should_log('tf_fail'):
                self.get_logger().warn(
                    "TF变换失败 (%s->%s): %s "
                    "(请确认 odometry/localization 节点正在发布此TF)",
                    BASE_FRAME, LOCAL_FRAME, str(e))
            raise

    # ============================================================
    # 获取机器人位置 (local 系)
    # ============================================================
    def get_robot_position(self):
        try:
            if self.tf_buffer.can_transform(
                    LOCAL_FRAME, BASE_FRAME, Time(),
                    timeout=Duration(seconds=0.05)):
                transform = self.tf_buffer.lookup_transform(
                    LOCAL_FRAME, BASE_FRAME, Time())
                return (transform.transform.translation.x,
                        transform.transform.translation.y)
        except (LookupException, ConnectivityException,
                ExtrapolationException) as e:
            if self.throttle.should_log('robot_tf'):
                self.get_logger().warn(
                    "[TF] 获取机器人位置失败 (%s->%s): %s" %
                    (LOCAL_FRAME, BASE_FRAME, str(e)))
        return None

    # ============================================================
    # 面包屑 -> Path 消息
    # ============================================================
    def breadcrumbs_to_path_msg(self, breadcrumbs, frame_id=None):
        if frame_id is None:
            frame_id = LOCAL_FRAME
        path_msg = Path()
        path_msg.header.frame_id = frame_id
        path_msg.header.stamp = self.get_clock().now().to_msg()

        if not breadcrumbs:
            return path_msg

        # ★ 步骤1: 距离过滤 — 相邻发布点间距 >= PATH_VIZ_MIN_DIST, 始终保留首尾
        filtered = [breadcrumbs[0]]
        for bx, by, bts in breadcrumbs[1:-1]:
            last = filtered[-1]
            if math.hypot(bx - last[0], by - last[1]) >= PATH_VIZ_MIN_DIST:
                filtered.append((bx, by, bts))
        filtered.append(breadcrumbs[-1])  # 始终保留终点

        # ★ 步骤2: 数量安全帽 — 如果距离过滤后仍超上限, 再做等步长降采样
        pts = filtered
        n = len(pts)
        if n > PATH_VIZ_MAX_POINTS:
            step = n / float(PATH_VIZ_MAX_POINTS)
            indices = [int(i * step) for i in range(PATH_VIZ_MAX_POINTS)]
            if indices[-1] != n - 1:
                indices[-1] = n - 1
            pts = [pts[i] for i in indices]

        for bx, by, bts in pts:
            pose = PoseStamped()
            pose.header.frame_id = frame_id
            pose.header.stamp = sec_to_time_msg(bts)
            pose.pose.position.x = bx
            pose.pose.position.y = by
            pose.pose.position.z = 0.0
            pose.pose.orientation.w = 1.0
            path_msg.poses.append(pose)
        return path_msg

    # ============================================================
    # 偏航角 → 四元数 (仅绕Z轴旋转)
    # ============================================================
    @staticmethod
    def yaw_to_quaternion(yaw):
        from geometry_msgs.msg import Quaternion
        q = Quaternion()
        q.x = 0.0
        q.y = 0.0
        q.z = math.sin(yaw / 2.0)
        q.w = math.cos(yaw / 2.0)
        return q

    # ============================================================
    # 从路径最后一段计算延伸方向
    # ============================================================
    @staticmethod
    def compute_path_direction(trimmed_path):
        if len(trimmed_path) < 2:
            return None
        dx = trimmed_path[-1][0] - trimmed_path[-2][0]
        dy = trimmed_path[-1][1] - trimmed_path[-2][1]
        return math.atan2(dy, dx)

    # ============================================================
    # 发送单点到 Nav2 NavigateToPose
    # ============================================================
    def send_goal_point_to_nav2(self, goal_x, goal_y, robot_pos, yaw=None):
        if robot_pos is not None:
            dist_to_goal = math.hypot(goal_x - robot_pos[0],
                                      goal_y - robot_pos[1])
            if dist_to_goal < NAV2_DEAD_ZONE_DIST:
                self.stats['goals_skipped'] += 1
                return

        move_dist = math.hypot(goal_x - self.last_goal_x,
                               goal_y - self.last_goal_y)
        if move_dist < NAV2_MIN_MOVE_DIST:
            self.stats['goals_skipped'] += 1
            return

        self.last_goal_x = goal_x
        self.last_goal_y = goal_y

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = NAV2_GOAL_FRAME
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = goal_x
        goal_msg.pose.pose.position.y = goal_y
        goal_msg.pose.pose.position.z = 0.0

        if yaw is None:
            yaw = 0.0
        goal_msg.pose.pose.orientation = self.yaw_to_quaternion(yaw)

        if self.action_client.wait_for_server(timeout_sec=1.0):
            self.action_client.send_goal_async(goal_msg)
            self.stats['goals_sent'] += 1
        else:
            if self.throttle.should_log('nav2_server'):
                self.get_logger().warn(
                    "等待 Nav2 '%s' Action 服务超时!" % NAV2_ACTION_NAME)

    # ============================================================
    # 处理回调 (按 PROCESSING_RATE Hz, 每tick排空队列批量处理)
    # ============================================================
    def processing_callback(self):
        # ---- 排空队列 ----
        frames = []
        while True:
            try:
                frames.append(self.frame_queue.get_nowait())
            except Queue.Empty:
                break

        if not frames:
            return

        # ---- 诊断: 单批次丢帧计数器 ----
        diag = {'batch': len(frames), 'drift': 0, 'jump': 0, 'tf_fail': 0, 'ok': 0}

        # ---- 逐帧跑流水线 ----
        last_pt_local = None
        last_mx_f = None
        last_my_f = None
        last_ekf_x = None
        last_ekf_y = None
        last_ekf_vx = None
        last_ekf_vy = None
        last_ekf_ok = False
        last_frame_item = None

        for frame_item in frames:
            self.stats['consumed'] += 1

            # 步骤1: AoA漂移检测
            if self.drift_detector.check(frame_item['raw_dis'],
                                         frame_item['raw_azi']):
                self.stats['drift_skipped'] += 1
                diag['drift'] += 1
                self.last_raw_dis = None
                self.last_raw_azi = None
                self.ekf.reset()                      # ★ 漂移时复位EKF
                continue

            # 步骤2: 跳变滤波
            if self.last_raw_dis is not None:
                delta_dis = abs(frame_item['raw_dis'] - self.last_raw_dis)
                delta_azi = abs(frame_item['raw_azi'] - self.last_raw_azi)
                if delta_azi > 180:
                    delta_azi = 360 - delta_azi
                if delta_dis > MAX_DIS_JUMP or delta_azi > MAX_AZI_JUMP:
                    if self.throttle.should_log('jump'):
                        self.get_logger().warn(
                            "[跳变丢弃] delta_dis=%.2fm delta_azi=%.1f deg "
                            "threshold(%.2fm/%.0f deg)" %
                            (delta_dis, delta_azi, MAX_DIS_JUMP, MAX_AZI_JUMP))
                    self.stats['skipped'] += 1
                    diag['jump'] += 1
                    continue
            self.last_raw_dis = frame_item['raw_dis']
            self.last_raw_azi = frame_item['raw_azi']

            # 步骤3: TF变换 (若TF不可用, 直接用raw_x/raw_y当local坐标)
            try:
                pt_local = self.transform_to_local(frame_item)
            except Exception:
                diag['tf_fail'] += 1
                self.get_logger().info("TF变换失败")
                continue

            diag['ok'] += 1

            # 步骤4: local系中值滤波
            mx_f, my_f = self.median.filter(pt_local.point.x, pt_local.point.y)
            # ★ 使用帧的实际到达时间戳 (而非处理时刻), 保证EKF的dt准确反映UWB采样间隔
            now_ts = frame_item['stamp']

            # ★ 步骤4.5: EKF滤波 — 用中值滤波输出作为观测
            ekf_x, ekf_y, ekf_vx, ekf_vy, ekf_converged = self.ekf.step(
                mx_f, my_f, now_ts)

            # ★ 步骤5: 面包屑 (用EKF输出替代中值滤波输出)
            if (self.last_bc_point is None or
                    math.hypot(ekf_x - self.last_bc_point[0],
                               ekf_y - self.last_bc_point[1]) > BREADCRUMB_DIST):
                self.breadcrumb.append((ekf_x, ekf_y, now_ts))
                self.last_bc_point = (ekf_x, ekf_y)
                while len(self.breadcrumb) > BREADCRUMB_MAX_SIZE:
                    self.breadcrumb.pop(0)

            last_pt_local = pt_local
            last_mx_f = mx_f
            last_my_f = my_f
            last_ekf_x = ekf_x
            last_ekf_y = ekf_y
            last_ekf_vx = ekf_vx
            last_ekf_vy = ekf_vy
            last_ekf_ok = ekf_converged
            last_frame_item = frame_item

        # ---- 诊断: 单批次丢帧汇总 (节流5秒) ----
        if self.throttle.should_log('diag'):
            self.get_logger().info(
                "[诊断] batch=%d ok=%d drift=%d jump=%d tf_fail=%d "
                "last_dis=%.2f last_azi=%.0f" %
                (diag['batch'], diag['ok'], diag['drift'],
                 diag['jump'], diag['tf_fail'],
                 frames[-1]['raw_dis'] if frames else -1,
                 frames[-1]['raw_azi'] if frames else -1))

        # ---- 没有成功处理的帧, 不发布 ----
        if last_frame_item is None:
            return

        frame_item = last_frame_item
        pt_local = last_pt_local
        mx_f = last_mx_f
        my_f = last_my_f
        ekf_x = last_ekf_x
        ekf_y = last_ekf_y
        ekf_vx = last_ekf_vx
        ekf_vy = last_ekf_vy

        # ---- 节流发布 + Nav2 目标发送 ----
        now_t = time_mod.time()
        if now_t - self.last_publish_time < PUBLISH_INTERVAL:
            return
        self.last_publish_time = now_t

        # --- 发布 local 系原始点 ---
        self.pub_local_raw.publish(pt_local)

        # --- 发布 local 系中值滤波点 ---
        pt_filt = PointStamped()
        pt_filt.header.stamp = self.get_clock().now().to_msg()
        pt_filt.header.frame_id = LOCAL_FRAME
        pt_filt.point.x = mx_f
        pt_filt.point.y = my_f
        pt_filt.point.z = 0.0
        self.pub_local_filt.publish(pt_filt)

        # --- 发布 EKF 滤波点 ---
        pt_ekf = PointStamped()
        pt_ekf.header.stamp = self.get_clock().now().to_msg()
        pt_ekf.header.frame_id = LOCAL_FRAME
        pt_ekf.point.x = ekf_x
        pt_ekf.point.y = ekf_y
        pt_ekf.point.z = 0.0
        self.pub_ekf.publish(pt_ekf)

        # --- 发布原始面包屑路径 (EKF输出构成) ---
        self.pub_path.publish(self.breadcrumbs_to_path_msg(self.breadcrumb))

        # --- 回退合并 (去迂回) ---
        if len(self.breadcrumb) >= 3:
            optimized = remove_backtrack_loops(
                self.breadcrumb,
                spatial_threshold=BACKTRACK_SPATIAL_THRESHOLD,
                detour_ratio=BACKTRACK_DETOUR_RATIO,
                max_search_ahead=BACKTRACK_MAX_SEARCH_AHEAD)
        else:
            optimized = list(self.breadcrumb)

        self.pub_opt_path.publish(self.breadcrumbs_to_path_msg(optimized))

        # --- 获取机器人位置 ---
        robot_pos = self.get_robot_position()

        # --- 截断 ---
        if robot_pos is not None and len(optimized) > TRIM_MIN_TRAIL_POINTS:
            trimmed = trim_from_robot(
                robot_pos, optimized,
                min_trail_points=TRIM_MIN_TRAIL_POINTS,
                throttle=self.throttle,
                logger=self.get_logger())
        else:
            if robot_pos is None:
                self.stats['robot_tf_fail'] += 1
            trimmed = list(optimized)

        self.pub_trim_path.publish(self.breadcrumbs_to_path_msg(trimmed))

        # --- 信标目标点 + MoveBase 发送 ---
        if len(trimmed) > 0:
            beacon_x = trimmed[-1][0]
            beacon_y = trimmed[-1][1]

            beacon_pt = PointStamped()
            beacon_pt.header.stamp = self.get_clock().now().to_msg()
            beacon_pt.header.frame_id = LOCAL_FRAME
            beacon_pt.point.x = beacon_x
            beacon_pt.point.y = beacon_y
            beacon_pt.point.z = 0.0
            self.pub_beacon.publish(beacon_pt)

            path_yaw = self.compute_path_direction(trimmed)
            self.send_goal_point_to_nav2(beacon_x, beacon_y, robot_pos, yaw=path_yaw)

        # --- 日志 ---
        now_ts = time_mod.time()
        latency_ms = (now_ts - frame_item['stamp']) * 1000.0
        beacon_str = ""
        if len(trimmed) > 0:
            beacon_str = " beacon(%.2f,%.2f)" % (trimmed[-1][0], trimmed[-1][1])
        self.get_logger().info(
            "dis=%.2fm azi=%.0f med(%.2f,%.2f) ekf(%.2f,%.2f v=%.2f,%.2f ok=%d) "
            "lat=%.0fms robot=%s%s "
            "bc=%d opt=%d trim=%d goals(sent=%d skip=%d) "
            "batch=%d c=%d dr=%d sk=%d rtf=%d" %
            (frame_item['raw_dis'], frame_item['raw_azi'],
             mx_f, my_f,
             ekf_x, ekf_y, ekf_vx, ekf_vy, last_ekf_ok,
             latency_ms,
             "(%.2f,%.2f)" % robot_pos if robot_pos else "N/A", beacon_str,
             len(self.breadcrumb), len(optimized), len(trimmed),
             self.stats['goals_sent'], self.stats['goals_skipped'],
             len(frames), self.stats['consumed'],
             self.stats['drift_skipped'], self.stats['skipped'],
             self.stats['robot_tf_fail']))

    def destroy_node(self):
        self.get_logger().info("[主线程] 正在关闭...")
        self.stop_event.set()
        self.reader.join(timeout=2.0)
        if self.reader.is_alive():
            self.get_logger().warn("[主线程] 串口线程未能及时退出 (join超时)")
        self.get_logger().info(
            "[主线程] 最终统计: consumed=%d drift_skipped=%d "
            "jump_skipped=%d robot_tf_fail=%d "
            "goals_sent=%d goals_skip=%d" %
            (self.stats['consumed'], self.stats['drift_skipped'],
             self.stats['skipped'], self.stats['robot_tf_fail'],
             self.stats['goals_sent'], self.stats['goals_skipped']))
        self.get_logger().info("[uwb_nav2_point_ekf] 已退出")
        super().destroy_node()


# ============================================================
# 入口
# ============================================================
def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = UwbNav2PointEkfNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        if node:
            node.get_logger().info(
                "[uwb_nav2_point_ekf] 收到 KeyboardInterrupt, 退出...")
    except Exception as e:
        if node:
            node.get_logger().error("发生异常: %s" % str(e))
        raise
    finally:
        if node:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
