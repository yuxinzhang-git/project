# 灭火狗

这是一个基于 ROS1 的火情识别与点位发布小项目，核心由两个脚本组成：

- `fire_action_node.py`：对外提供 `fire_action` 服务，负责启动、停止和查询火情匹配状态
- `fire_match.py`：完成 MQTT 接收、图像模板匹配、深度估计、TF 坐标变换和点位发布

## 项目目标

当 MQTT 收到指定火情模板后，节点会开始从相机图像中做多帧匹配，结合深度图估计目标空间位置，最后把结果发布到 `/clicked_point`，方便在 RViz 或下游模块中使用。

## 文件说明

### `fire_action_node.py`

- 启动 ROS 节点 `fire_action_node`
- 提供 `fire_action` 服务
- 支持三个指令：
  - `start`
  - `stop`
  - `status`
- 内部通过 `FireTemplateMatcher` 控制匹配流程

### `fire_match.py`

- 订阅彩色图像：`/camera/color/image_raw`
- 订阅深度图像：`/camera/aligned_depth_to_color/image_raw`
- 订阅 MQTT 主题：`mqtt/face/1033360/Snap`
- 从 MQTT 中提取模板图片
- 进行多尺度模板匹配
- 结合深度图计算目标点
- 发布 `/clicked_point`

## 运行依赖

- ROS1
- `rospy`
- `cv_bridge`
- `opencv-python` 或系统 OpenCV
- `numpy`
- `paho-mqtt`
- `tf`
- 自定义服务 `tool/Invoke`

## 运行前配置

脚本里有几项硬编码配置，运行前通常需要确认：

- `fire_action_node.py`
  - `ROS_MASTER_URI`
  - `ROS_IP`
- `fire_match.py`
  - MQTT broker：`BROKER_IP`
  - MQTT 主题：`MQTT_TOPIC`
  - 模板保存目录：`SAVE_DIR`
  - 相机内参：`FX`、`FY`、`CX`、`CY`

## 工作流程

1. 启动 `fire_action_node.py`
2. 通过 `fire_action` 服务发送 `start`
3. 节点订阅相机和 MQTT
4. MQTT 收到模板图后，开始采集多帧图像
5. 在彩色图中做多尺度模板匹配
6. 从深度图估计目标距离
7. 计算空间点并尝试变换到 `map`
8. 发布结果到 `/clicked_point`

## 服务接口

服务名：`fire_action`

请求内容：

- `start`：启动匹配
- `stop`：停止匹配
- `status`：查询当前状态

返回内容：

- `ok`
- `already start`
- `already stop`
- `running`
- `stopped`
- `error: unknown command`

## 常见话题

- `/camera/color/image_raw`
- `/camera/aligned_depth_to_color/image_raw`
- `/clicked_point`

## 说明

- 模板来源是 MQTT 消息中的 `info.pic`
- 当前代码默认只接受 `operator == "FireSmokeSnapPush"`
- 保存的匹配结果图片会写入 `SAVE_DIR`
- 如果 TF 变换失败，会直接发布本地坐标点

## 使用示例

启动服务节点后，可以通过 ROS service 调用：

```bash
rosservice call /fire_action "request: 'start'"
rosservice call /fire_action "request: 'status'"
rosservice call /fire_action "request: 'stop'"
```

## 备注

这个项目目前更像是一个单机联调版本，配置项和地址大多写死在脚本里。后续如果要部署到别的机器，建议把 MQTT、相机和 TF 相关参数集中到 launch 文件或参数服务器里。
