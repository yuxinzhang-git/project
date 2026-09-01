# HydroGuard（水电站智能视觉告警复核系统）


## 项目简介

HydroGuard 是一个面向水电站场景的智能视频告警处理服务。项目通过 FFmpeg 从 RTSP 或视频文件中抽取图像帧，调用外部检测/跟踪接口进行小模型识别，再按事件类型调用视觉大模型或标签模型做二次复核，最终将确认后的告警推送到业务平台。

项目同时支持热成像/摄像头设备主动上报的告警图片，通过 FastAPI 接收 multipart 表单，解析 XML 告警内容，并将图片封装成统一告警格式上报。

## 主要能力

- 视频流抽帧与短帧缓存
- 小模型目标检测与轨迹检测
- 大模型图像复核
- ROI 区域过滤
- 多事件告警映射
- 告警抑制，避免短时间重复上报
- 高温告警图片接入
- 告警图片、区域框、发生时间封装
- HTTP 推送到水电站告警平台

## 支持的事件

代码中主要覆盖以下事件类型：

- 浓烟
- 火焰
- 火花
- 游泳
- 人员闯入
- 漏水
- 漏油
- 漂浮物
- 高温
- 抛洒物
- 行人
- 施工人员
- 摩托车
- 停车
- 逆行
- 拥堵

不同事件会根据配置启用，并可能经过小模型、跟踪模型、标签模型或视觉大模型复核。

## 文件说明

- `stream.py`
  - 主视频流处理入口
  - 加载 JSON 配置
  - 启动 FFmpeg 抽帧
  - 调用检测、跟踪、复核和告警推送流程

- `env.py`
  - 事件运行环境
  - 管理事件开关、事件映射、复核任务、告警抑制状态
  - 内置 `/alarm` FastAPI 接口，用于接收高温等设备告警

- `scene.py`
  - 小模型检测与场景判断封装
  - 调用检测接口、火焰/烟雾接口和跟踪接口
  - 负责 ROI 过滤、置信度阈值判断和高温告警缓存读取

- `handler.py`
  - 各类事件的复核逻辑
  - 包含烟火、浓烟、火焰、火花、游泳、人员闯入、漏水、漏油、漂浮物、行人、摩托车等处理函数

- `ffmpeg.py`
  - FFmpeg 子进程封装
  - 从 RTSP 或视频文件中抽取 JPEG 帧
  - 支持帧停滞监控和自动重启

- `frame.py`
  - 图像帧对象
  - 提供 JPEG 解析、base64 编码、裁剪、缩放、锐化、去模糊和拼接能力

- `tracker.py`
  - 轨迹跟踪接口封装
  - 维护目标轨迹历史

- `result.py`
  - 告警结果和目标框的数据结构

- `buffer.py`
  - 基于 asyncio 的协程安全环形缓冲区

- `aio.py`
  - 异步 HTTP GET/POST 工具
  - 视觉大模型会话封装

- `alarm_fastapi.py`
  - 独立 FastAPI 告警接收服务
  - 解析设备 multipart 告警和 XML 内容
  - 将上传图片转成 base64 后推送到告警平台

- `event_notification_alert.py`
  - 设备告警 XML 对应的数据类

- `docker-compose.yml`
  - `alarm_fastapi.py` 的容器化运行配置

## 核心流程

### 视频流告警流程

1. `stream.py` 启动并加载配置
2. `Ffmpeg` 从 RTSP、视频文件或图片源抽取图像帧
3. 最近帧被写入 `AsyncioRingBuffer`
4. `Scene` 调用外部检测/跟踪服务
5. 小模型事件被映射为业务事件
6. `Env` 判断是否需要复核、是否处于告警抑制期
7. `handler.py` 中的复核函数调用视觉大模型或标签模型
8. 复核通过后，`Stream.push_alarm()` 组装告警 JSON
9. 告警推送到 `PushUrl`

### 设备告警流程

1. 摄像头或热成像设备向 `/alarm` POST multipart 表单
2. 服务读取 `TMPA` XML 字段
3. 使用 `xsdata` 解析为 `EventNotificationAlert`
4. 读取 `backgroundPic` 或 `thermalPic`
5. 图片转 base64
6. 推送到告警平台

## 运行依赖

主要 Python 依赖：

- Python 3.10+
- `fastapi`
- `uvicorn`
- `aiohttp`
- `python-multipart`
- `xsdata`
- `opencv-python`
- `numpy`
- `requests`

安装示例：

```bash
pip install fastapi uvicorn aiohttp python-multipart xsdata opencv-python numpy requests
```

还需要：

- FFmpeg
- 外部检测服务
- 外部跟踪服务
- 外部火焰/烟雾检测服务
- 视觉大模型服务
- 告警推送平台接口

注意：`handler.py` 中引用了 `reward.py` 和 `label.py`，但当前目录没有这两个文件。运行完整复核链路前，需要确认这两个模块来自同级目录、上层工程或运行环境镜像。

## 运行方式

### 启动视频流处理

使用配置文件：

```bash
python stream.py --config config.json --name stream-1-1 --log-level INFO
```

不传配置文件时，代码会使用默认 RTSP 地址和默认事件注册逻辑：

```bash
python stream.py
```

### 启动独立告警接收服务

```bash
python alarm_fastapi.py
```

默认监听：

```text
0.0.0.0:15000
```

接口：

```text
POST /alarm
```

### Docker Compose

```bash
docker compose up -d
```

当前 `docker-compose.yml` 使用 host 网络，并将 `/home/xiezuo/beta/aiod/python` 挂载到容器内 `/stream/`。

## 配置项

`stream.py` 支持从 JSON 配置读取以下字段：

- `MediaName`：摄像头或媒体名称
- `Refer`：测站编码
- `PlayUrl`：RTSP、视频文件或图片路径
- `PushUrl`：告警推送地址
- `AlarmDuration`：告警抑制时间，单位分钟
- `AlarmEnabled`：是否启用告警上报
- `ROI`：告警区域
- `Enabled`：事件开关
- `StreamOpt`：检测相关参数
- `TrackUrl`：跟踪服务地址
- `DetectUrl`：通用检测服务地址
- `FireUrl`：烟火检测服务地址
- `TokenUrl`：标签模型 token 地址
- `LabelUrl`：标签模型概率地址
- `Direction`：道路或画面主方向配置

## 告警推送格式

告警上报时会组装类似结构：

```json
{
  "Stcd": "测站编码",
  "Device": "设备或任务标识",
  "Camera": "摄像头_事件_任务名",
  "AlarmType": "告警类型",
  "Data": "base64图片",
  "Occur": "发生时间",
  "Result": {
    "Files": [
      {
        "Width": 1920,
        "Height": 1080,
        "Regions": []
      }
    ]
  }
}
```

如果检测结果包含目标框，`Regions` 中会追加归一化坐标区域。

## 运行前检查

- FFmpeg 路径是否正确，默认是 `/beta/ffmpeg/bin/ffmpeg`
- RTSP 地址或视频文件路径是否可访问
- `PushUrl` 是否可访问
- 检测、跟踪、火焰识别、大模型服务地址是否可访问
- `reward.py`、`label.py` 是否在 Python 路径中
- 容器运行时挂载路径是否与实际部署路径一致
- 如果启用高温告警，`/alarm` 端口是否开放


## 备注

当前项目中存在较多硬编码内网地址和测试路径，适合联调环境快速运行。正式部署前，建议将服务地址、FFmpeg 路径、模型参数、告警抑制时间和事件开关统一放入配置文件或环境变量。
