import cv2
import numpy as np
import signal
import sys

# ====================== 【你只需要改这里】 ======================
IMAGE_PATH    = "frame_3.jpg"          # 你的图像
POINTCLOUD_PATH = "cloud_3.npy"        # 你的点云
CAMERA_INTRINSIC = "calibration_result.npz"  # 相机内参
EXTRINSIC_FILE = "final_extrinsics.npz"      # 你刚才调好的外参
# =================================================================

# ====================== Ctrl+C 退出处理 ======================
def signal_handler(sig, frame):
    print("\nCtrl+C 退出程序")
    cv2.destroyAllWindows()
    sys.exit(0)

# 注册 Ctrl+C 信号
signal.signal(signal.SIGINT, signal_handler)
# =================================================================

# ====================== 【新增】终端输入深度范围 ======================
print("="*50)
print("请输入深度范围（相机前方 Z 轴距离，单位：米）")
while True:
    try:
        min_depth = float(input("输入最小深度 min_depth："))
        max_depth = float(input("输入最大深度 max_depth："))
        if min_depth >= max_depth:
            print("错误：最小深度必须小于最大深度！请重新输入\n")
            continue
        if min_depth < 0.1:
            print("警告：最小深度建议 >= 0.1 米\n")
        break
    except ValueError:
        print("错误：请输入数字！\n")

print(f"\n已设置深度范围：{min_depth:.2f} ~ {max_depth:.2f} 米")
print("="*50)
# ====================================================================

# --------------------- 1. 加载所有参数 ---------------------
# 相机内参
K = np.load(CAMERA_INTRINSIC)["camera_matrix"]

# 外参 R, t（你手动标定好的！）
ext = np.load(EXTRINSIC_FILE)
R = ext["R"]
t = ext["t"]

# 加载图像和点云
img = cv2.imread(IMAGE_PATH)
points = np.load(POINTCLOUD_PATH)

h, w = img.shape[:2]

# --------------------- 2. 点云投影核心函数（已加深度过滤） ---------------------
def project_points(points, R, t, K, min_depth, max_depth):
    valid_front = (points[:, 0] > 0)
    points = points[valid_front]
    
    # 把雷达点云转到相机坐标系
    pts_cam = (R @ points.T).T + t

    # 只保留相机前方的点
    valid = pts_cam[:, 2] > 0.1

    # ====================== 【新增】深度范围过滤 ======================
    depths = pts_cam[:, 2]
    valid &= (depths >= min_depth) & (depths <= max_depth)
    # ==================================================================

    pts = pts_cam[valid]
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]

    # 3D → 2D 像素坐标
    fx, fy = K[0,0], K[1,1]
    cx, cy = K[0,2], K[1,2]

    u = (fx * x / z + cx).astype(int)
    v = (fy * y / z + cy).astype(int)

    # 只保留在图像范围内的点
    mask = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    return u[mask], v[mask]

# --------------------- 3. 执行投影（传入深度范围） ---------------------
u, v = project_points(points, R, t, K, min_depth, max_depth)

# --------------------- 4. 绘制到图像上 ---------------------
result = img.copy()
for ui, vi in zip(u, v):
    cv2.circle(result, (ui, vi), 1, (0, 255, 0), -1)

# ====================== 【新增】在图像上显示深度范围 ======================
text = f"Depth: {min_depth:.1f} ~ {max_depth:.1f} m | Points: {len(u)}"
cv2.putText(result, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
# ========================================================================

# --------------------- 5. 显示 + 保存结果 ---------------------
cv2.imshow("Auto Projection Result", result)
cv2.imwrite("projection_result.jpg", result)  # 保存成品图

print(f"R:{R}")
print(f"t:{t}")
print(f"\n投影完成！共绘制 {len(u)} 个点")
print("结果已保存为: projection_result.jpg")
print("按 ESC 或 Ctrl+C 均可退出")

# Linux 稳定循环
while True:
    key = cv2.waitKey(50) & 0xFF
    if key == 27:  # ESC
        print("\nESC 退出程序")
        break

cv2.destroyAllWindows()
