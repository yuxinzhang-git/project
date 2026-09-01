import cv2
import numpy as np
import time

# ======================== 参数配置 ========================
CALIB_FILE = "calibration_result.npz"   # 摄像头内参
IMAGE_FILE = "frame_3.jpg"              # 单目图片
POINTCLOUD_FILE = "cloud_3.npy"         # 点云数据
SCALE = 1.5

INIT_MIN_DIST = 0.3
INIT_MAX_DIST = 6.0
DIST_MAX_RANGE = 10.0
# =========================================================

# 加载内参
data = np.load(CALIB_FILE)
K = data["camera_matrix"]
dist = data["dist_coeffs"]

# 加载图像
img = cv2.imread(IMAGE_FILE)
if img is None:
    raise Exception(f"无法读取图像: {IMAGE_FILE}")

# 加载点云
points = np.load(POINTCLOUD_FILE)
print(f"加载点云数量: {len(points)}")
print("X range:", points[:,0].min(), points[:,0].max())
print("Y range:", points[:,1].min(), points[:,1].max())
print("Z range:", points[:,2].min(), points[:,2].max())

h, w = img.shape[:2]
new_w = int(w * SCALE)
new_h = int(h * SCALE)

# 创建窗口
cv2.namedWindow("Projection Viewer", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Projection Viewer", new_w, new_h)

# ==================== 定义基准变换（雷达 → 相机） ====================
# 雷达坐标系: X前, Y左, Z上
# 相机坐标系: X右, Y下, Z前 (OpenCV)
R_corr = np.array([[0, 1, 0],    # 雷达 Y(左) -> 相机 X(右)
                   [0, 0, -1],   # 雷达 Z(上) -> 相机 -Y(下)
                   [1, 0, 0]])   # 雷达 X(前) -> 相机 Z(前)
t_corr = np.array([0.0, 0.0, 0.0])  # 基准平移（可根据实际安装微调，例如相机在雷达后方0.2米可设t_corr[2]=0.2）
# ==================================================================

# 创建滑条（控制相对于基准的微调）
cv2.createTrackbar("Roll",  "Projection Viewer", 90, 180, lambda x: None)   # 微调范围 ±90°
cv2.createTrackbar("Pitch","Projection Viewer", 90, 180, lambda x: None)
cv2.createTrackbar("Yaw",  "Projection Viewer", 90, 180, lambda x: None)
cv2.createTrackbar("tx",   "Projection Viewer", 50, 100, lambda x: None)    
cv2.createTrackbar("ty",   "Projection Viewer", 50, 100, lambda x: None)
cv2.createTrackbar("tz",   "Projection Viewer", 50, 100, lambda x: None)

cv2.createTrackbar("MinDepth", "Projection Viewer",
                   int(INIT_MIN_DIST * 100), int(DIST_MAX_RANGE * 100), lambda x: None)
cv2.createTrackbar("MaxDepth", "Projection Viewer",
                   int(INIT_MAX_DIST * 100), int(DIST_MAX_RANGE * 100), lambda x: None)

def get_params():
    # 滑条值 0~180 -> 角度 -90° ~ +90°
    roll  = (cv2.getTrackbarPos("Roll",  "Projection Viewer") - 90) * np.pi / 180
    pitch = (cv2.getTrackbarPos("Pitch", "Projection Viewer") - 90) * np.pi / 180
    yaw   = (cv2.getTrackbarPos("Yaw",   "Projection Viewer") - 90) * np.pi / 180

    tx = (cv2.getTrackbarPos("tx", "Projection Viewer") - 50) / 25.0
    ty = (cv2.getTrackbarPos("ty", "Projection Viewer") - 50) / 25.0
    tz = (cv2.getTrackbarPos("tz", "Projection Viewer") - 50) / 25.0

    min_d = cv2.getTrackbarPos("MinDepth", "Projection Viewer") / 100.0
    max_d = cv2.getTrackbarPos("MaxDepth", "Projection Viewer") / 100.0
    if min_d >= max_d:
        min_d = max_d - 0.1

    return roll, pitch, yaw, tx, ty, tz, min_d, max_d

def rpy_to_R(roll, pitch, yaw):
    """固定轴 ZYX 顺序（先绕X，再绕Y，最后绕Z）"""
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(pitch), -np.sin(pitch)],
                   [0, np.sin(pitch),  np.cos(pitch)]])
    Ry = np.array([[ np.cos(yaw), 0, np.sin(yaw)],
                   [0, 1, 0],
                   [-np.sin(yaw), 0, np.cos(yaw)]])
    Rz = np.array([[np.cos(roll), -np.sin(roll), 0],
                   [np.sin(roll),  np.cos(roll), 0],
                   [0, 0, 1]])
    return Rx @ Ry @ Rz   # 外旋: 先z, 再Y, 再x

def project(points, R_user, t_user, K, min_depth, max_depth):
    """
    输入:
        points: (N,3) 雷达坐标系点云
        R_user: 用户微调旋转矩阵 (3x3)
        t_user: 用户微调平移向量 (3,)
        K: 相机内参
        min_depth, max_depth: 深度过滤范围
    输出:
        uv: (M,2) 投影到图像上的像素坐标（原始图像尺寸）
    """
    # 1. 原始点云过滤：高度 (Z 轴)
    valid_height = (points[:, 2] >= -0.20)
    pts = points[valid_height]

    # 2. 保留雷达前方的点 (X 轴正向)
    valid_front = (pts[:, 0] > 0)
    pts = pts[valid_front]

    # 3. 应用基准变换（雷达 → 相机）
    pts_cam = pts @ R_corr.T + t_corr

    # 4. 应用用户微调（相对于基准的额外旋转平移）
    pts_cam = pts_cam @ R_user.T + t_user

    # 5. 保留相机前方的点 (Z_cam > 0.1)
    valid = pts_cam[:, 2] > 0.1
    depths = pts_cam[:, 2]

    # 6. 深度范围过滤
    valid &= (depths >= min_depth) & (depths <= max_depth)
    pts_final = pts_cam[valid]

    if len(pts_final) == 0:
        return np.empty((0, 2), dtype=int)

    # 7. 投影到图像平面
    x, y, z = pts_final[:,0], pts_final[:,1], pts_final[:,2]
    fx, fy = K[0,0], K[1,1]
    cx, cy = K[0,2], K[1,2]
    u = (fx * x / z + cx).astype(int)
    v = (fy * y / z + cy).astype(int)

    return np.stack([u, v], axis=1)

# 主循环
while True:
    roll, pitch, yaw, tx, ty, tz, min_d, max_d = get_params()
    R_user = rpy_to_R(roll, pitch, yaw)
    t_user = np.array([tx, ty, tz])

    uv = project(points, R_user, t_user, K, min_d, max_d)

    # 绘制
    out = img.copy()
    for u, v in uv:
        if 0 <= u < w and 0 <= v < h:
            cv2.circle(out, (u, v), 1, (0, 255, 0), -1)

    out_resized = cv2.resize(out, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    cv2.putText(out_resized, f"Points: {len(uv)}", (10, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
    cv2.imshow("Projection Viewer", out_resized)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC 退出
        # 保存最终外参（基准 + 用户微调）
        R_final = R_user @ R_corr
        t_final = t_user + R_user @ t_corr
        np.savez("final_extrinsics.npz", R=R_final, t=t_final)
        print("已保存外参到 final_extrinsics.npz")
        break

cv2.destroyAllWindows()