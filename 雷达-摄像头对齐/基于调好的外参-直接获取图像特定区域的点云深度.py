import cv2
import numpy as np

# ================== 配置参数 ==================
IMAGE_PATH = "frame_1.jpg"
POINTCLOUD_PATH = "cloud_1.npy"
CAMERA_INTRINSIC = "calibration_result.npz"     # 相机内参
EXTRINSIC_FILE = "final_extrinsics.npz"   # 点云-单目标定文件

# 点云预处理参数
HEIGHT_MIN = -0.20   # 米
HEIGHT_MAX = 2.0     # 米
FRONT_AXIS = 0       # 0表示X轴为前方 (X>0)
# ============================================

# 全局变量
points_uv = None     # 预计算的投影点像素坐标 (N,2)
points_depth = None  # 对应的相机深度 (N,)
img_display = None   # 显示图像


def load_data():
    """加载所有数据"""
    # 相机内参
    data = np.load(CAMERA_INTRINSIC)
    K = data["camera_matrix"]
    
    # 外参
    ext = np.load(EXTRINSIC_FILE)
    R = ext["R"]
    t = ext["t"]
    
    # 图像
    img = cv2.imread(IMAGE_PATH)
    if img is None:
        raise FileNotFoundError(f"无法加载图像: {IMAGE_PATH}")
    
    # 点云
    points = np.load(POINTCLOUD_PATH)
    print(f"原始点云数量: {len(points)}")
    
    return K, R, t, img, points


def preprocess_pointcloud(points):
    """点云预处理"""
    # 高度过滤
    valid_height = (points[:, 2] >= HEIGHT_MIN) 
    points = points[valid_height]
    
    # 前方过滤 (X > 0)
    valid_front = (points[:, FRONT_AXIS] > 0)
    points = points[valid_front]
    
    print(f"预处理后点云数量: {len(points)}")
    return points


def project_points(points, R, t, K):
    """点云投影到图像像素"""
    # 雷达坐标系 -> 相机坐标系
    pts_cam = (R @ points.T).T + t
    
    # 保留相机前方的点
    valid = pts_cam[:, 2] > 0.1
    pts_cam = pts_cam[valid]
    depths = pts_cam[:, 2]
    
    # 投影到像素
    fx, fy = K[0,0], K[1,1]
    cx, cy = K[0,2], K[1,2]
    x, y, z = pts_cam[:, 0], pts_cam[:, 1], pts_cam[:, 2]
    u = (fx * x / z + cx).astype(int)
    v = (fy * y / z + cy).astype(int)
    
    return np.stack([u, v], axis=1), depths


def compute_avg_depth_in_roi(rect):
    """计算ROI内平均深度"""
    global points_uv, points_depth
    if points_uv is None or len(points_uv) == 0:
        return None
    
    x1, y1, x2, y2 = rect
    mask = (points_uv[:, 0] >= x1) & (points_uv[:, 0] <= x2) & \
           (points_uv[:, 1] >= y1) & (points_uv[:, 1] <= y2)
    selected_depths = points_depth[mask]
    if len(selected_depths) == 0:
        return None
    return np.mean(selected_depths)


def main():
    global img_display, points_uv, points_depth
    
    # 加载数据
    K, R, t, img, points_raw = load_data()
    h, w = img.shape[:2]
    
    # 预处理 + 投影
    points = preprocess_pointcloud(points_raw)
    points_uv, points_depth = project_points(points, R, t, K)
    print(f"有效投影点数量: {len(points_uv)}\n")
    
    # 绘制投影点
    img_display = img.copy()
    for (u, v) in points_uv:
        if 0 <= u < w and 0 <= v < h:
            cv2.circle(img_display, (u, v), 1, (0, 255, 0), -1)

    # ================== 终端输入坐标 ==================
    print("===== 深度计算工具 =====")
    print("请输入 左上角x1 左上角y1 右下角x2 右下角y2")
    print("示例输入: 176 293 203 336\n")
    
    while True:
        try:
            # 读取输入
            coords = input("请输入坐标(空格分隔) / 输入 q 退出: ")
            if coords.strip().lower() == 'q':
                print("退出程序")
                break
            
            # 解析坐标
            x1, y1, x2, y2 = map(int, coords.split())
            
            # 计算深度
            avg_depth = compute_avg_depth_in_roi((x1, y1, x2, y2))
            
            if avg_depth is not None:
                print(f"\n计算成功！")
                print(f"区域坐标：({x1},{y1}) -> ({x2},{y2})")
                print(f"平均深度：{avg_depth:.3f} 米\n")
            else:
                print("\n该区域内无点云投影，请更换坐标\n")
                
        except ValueError:
            print("\n输入格式错误！请输入 4 个数字，用空格分隔\n")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()