# 雷达-摄像头对齐

这个目录包含一组用于雷达点云与单目相机图像对齐的 Python 工具脚本。整体流程是：加载相机内参、图像和点云，通过可视化滑条调整雷达到相机的外参，然后用保存的外参验证点云投影效果，最后可在图像指定区域内查询对应点云深度。

## 文件说明

- `可视化滑动调参-保存最优的外参.py`
  - 使用 OpenCV 窗口和滑条手动调整雷达点云到相机图像的投影效果
  - ESC 退出时保存最终外参到 `final_extrinsics.npz`

- `基于调好的外参-验证点云投影到图像.py`
  - 加载已经保存的 `final_extrinsics.npz`
  - 将点云投影到图像上
  - 支持在终端输入深度过滤范围
  - 保存投影结果图 `projection_result.jpg`

- `基于调好的外参-直接获取图像特定区域的点云深度.py`
  - 加载图像、点云、相机内参和外参
  - 将点云预投影到图像平面
  - 在终端输入 ROI 坐标，计算该区域内点云的平均深度

## 输入文件

脚本默认使用以下文件名，运行前需要放在当前工作目录下，或修改脚本顶部配置：

- `calibration_result.npz`：相机内参文件，至少包含：
  - `camera_matrix`
  - `dist_coeffs`
- `frame_*.jpg`：相机图像
- `cloud_*.npy`：雷达点云，形状通常为 `(N, 3)`
- `final_extrinsics.npz`：手动调参后保存的雷达到相机外参

## 依赖

- Python 3
- OpenCV
- NumPy

安装示例：

```bash
pip install opencv-python numpy
```

## 坐标系约定

调参脚本中默认坐标系为：

- 雷达坐标系：`X` 向前，`Y` 向左，`Z` 向上
- 相机坐标系：`X` 向右，`Y` 向下，`Z` 向前

脚本内置了一个基础旋转矩阵 `R_corr`，用于完成雷达坐标系到 OpenCV 相机坐标系的初始转换。滑条调参是在这个基础变换上继续微调。

## 推荐使用流程

### 1. 手动调外参

确认以下文件存在：

- `calibration_result.npz`
- `frame_3.jpg`
- `cloud_3.npy`

运行：

```bash
python 可视化滑动调参-保存最优的外参.py
```

在窗口中调节：

- `Roll`
- `Pitch`
- `Yaw`
- `tx`
- `ty`
- `tz`
- `MinDepth`
- `MaxDepth`

当点云投影与图像中的真实物体基本对齐后，按 `ESC` 退出。程序会保存：

```text
final_extrinsics.npz
```

### 2. 验证投影结果

运行：

```bash
python 基于调好的外参-验证点云投影到图像.py
```

根据提示输入最小深度和最大深度。程序会显示投影结果，并保存：

```text
projection_result.jpg
```

### 3. 查询图像区域深度

确认 `final_extrinsics.npz` 已经生成，然后运行：

```bash
python 基于调好的外参-直接获取图像特定区域的点云深度.py
```

按提示输入 ROI 左上角和右下角坐标：

```text
176 293 203 336
```

程序会输出该区域内投影点云的平均深度，单位为米。

## 输出文件

- `final_extrinsics.npz`
  - `R`：雷达到相机的旋转矩阵
  - `t`：雷达到相机的平移向量

- `projection_result.jpg`
  - 点云投影到图像后的可视化结果

## 常见调整项

- 图像或点云编号不同：修改脚本顶部的 `IMAGE_FILE`、`IMAGE_PATH`、`POINTCLOUD_FILE`、`POINTCLOUD_PATH`
- 投影点太多或太少：调整 `MinDepth`、`MaxDepth` 或深度输入范围
- 点云高度干扰较多：调整 `HEIGHT_MIN`、`HEIGHT_MAX`
- 外参偏差较大：先确认雷达和相机坐标系约定是否一致，再重新调节 `Roll/Pitch/Yaw/tx/ty/tz`

## 注意事项

- 运行可视化脚本需要图形界面环境。
- `cv2.imshow` 在无桌面环境或 SSH 无转发时可能无法正常显示。
- 当前脚本以手动标定和离线验证为主，不包含实时 ROS/驱动采集流程。
- 调参时建议使用同一时刻或时间差较小的图像与点云，否则移动物体会影响对齐效果。
