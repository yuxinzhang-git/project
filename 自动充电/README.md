# `uwb_nav2_point_local_ekf.py`

这是一个面向 ROS 2 的 UWB 单点导航节点，作用是把串口 UWB 数据做清洗、滤波和 EKF 平滑后，转换成 `local` 坐标系下的目标点，并通过 Nav2 的 `NavigateToPose` action 发送给导航栈。

## 处理流程

1. 串口读取 UWB 帧
2. 方位角中值滤波
3. AoA 漂移检测
4. 跳变过滤
5. TF 转换到 `local`
6. 位置中值滤波
7. 2D 匀速 EKF
8. 面包屑轨迹累积
9. 回退段合并
10. 从机器人当前位置截断轨迹
11. 取最后一个点作为导航目标

## 发布话题

- `/uwb/raw_point_local`
- `/uwb/filtered_point`
- `/uwb/ekf_point`
- `/uwb/beacon_point`
- `/uwb/filtered_path`
- `/uwb/optimized_path`
- `/uwb/trimmed_path`

## 依赖

- ROS 2
- `nav2_msgs`
- `tf2_ros`
- `geometry_msgs`
- `nav_msgs`
- `pyserial`
- `numpy`

## 运行前提

- 串口设备默认是 `/dev/ttyACM0`
- 需要有 `base_link -> local` 的 TF
- 需要 Nav2 的 `navigate_to_pose` action 可用

## 使用

通常在 ROS 2 包中直接运行该脚本即可：

```bash
ros2 run <package_name> uwb_nav2_point_local_ekf.py
```

如果设备名、串口波特率或阈值要调整，直接修改脚本顶部的常量即可。

## 备注

- 这个版本已经去掉了 TF 失败后的冗余回退片段。
- EKF 的观测输入是中值滤波后的 local 坐标。
- 最终发给 Nav2 的是轨迹最后一个点，而不是整条路径。
