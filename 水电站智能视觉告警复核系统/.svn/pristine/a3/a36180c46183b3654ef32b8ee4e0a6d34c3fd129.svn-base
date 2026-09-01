import argparse
import asyncio
import json
import logging
import sys
import time

from aio import file2base64, async_http_post
from env import Env, Handler
from ffmpeg import Ffmpeg
from frame import get_jpeg_dimensions, Frame, stitch_images
from handler import (fire_handler, debris_handler, person_label_handler, motor_label_handler,
                     smoke_handler, flame_handler, spark_handler, swimming_handler, intrusion_handler,
                     water_leak_handler, oil_leak_handler, floating_debris_handler)
from result import Result, Object

# 配置日志系统
logger = logging.getLogger(__name__)
# 默认日志级别为INFO，可以通过环境变量或配置文件调整
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
# 不打印这个debug日志
logging.getLogger("python_multipart.multipart").disabled = True


class Stream:

    def __init__(self, name=None, config_path=None, log_level=None):
        self.name = name
        # 如果提供了日志级别，则设置日志级别
        if log_level:
            self._set_log_level(log_level)
        # self.play_url = 'rtsp://admin:Xiezuo01@192.168.1.56'
        self.play_url = '/mnt/144/测试集/停车/摩托车_44.114.36.4_通道61_K78+709_1744084310214.mp4'
        self.env = Env(self.name)
        self.ffmpeg = None
        self.alarm_url = 'http://192.168.1.65:3004/xzhydro/api/alarm/push'
        # self.alarm_url = ''
        self.conf = None

        self.ratio = 10  # 抽帧频率，单位：秒
        self.stcd = ''  # 测站编码
        self.camera = ''  # 摄像头名字
        self.device = ''  # 自己的名字从MYNAME环境变量获取, 一般是容器的名字, task id，batch id
        self.prompts = {}  # 大模型题词
        self.enabled = True  # 是否启动告警上报
        self.alarm_type = ''  # 告警类型，多个告警以'，'隔开，如：烟火,停车
        self.alarm_duration = 5  # 告警抑制事件，单位：分钟
        self.roi = []  # 告警区域
        self.prompt_config = None  # 存储当前使用的题词配置
        self._alarm_stat = {}  # 记录告警上报时间，用于告警抑制

        # 如果提供了配置文件路径，则加载配置
        if config_path:
            self.load_config(config_path)

    def _set_log_level(self, level):
        """设置日志级别
        
        Args:
            level: 日志级别，可以是 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' 或对应的数字
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

        if isinstance(level, str):
            level = level.upper()
            if level in level_map:
                logger.setLevel(level_map[level])
                # 同时设置根logger的级别
                logging.getLogger().setLevel(level_map[level])
                logger.info(f"日志级别已设置为: {level}")
            else:
                logger.warning(f"无效的日志级别: {level}，使用默认级别 INFO")
        elif isinstance(level, int):
            logger.setLevel(level)
            logging.getLogger().setLevel(level)
            logger.info(f"日志级别已设置为: {level}")

    def is_image(self):
        ext = self.play_url[-4:]
        if ext == '.jpg' or ext == '.png':
            return True
        return False

    def is_stitched_image(self):
        """检查是否是拼接图（通过文件名包含'stitch'或'拼接'来判断）"""
        if self.is_image():
            filename = self.play_url.lower()
            return 'stitch' in filename or '拼接' in filename
        return False

    def load_config(self, config_path):
        """从JSON配置文件加载配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"json config: {config}")
            # 映射配置到类属性
            self.camera = config.get('MediaName', self.camera)
            self.stcd = config.get('Refer', self.stcd)
            self.play_url = config.get('PlayUrl', self.play_url)
            self.alarm_url = config.get('PushUrl', self.alarm_url)
            occur_enable = config.get('Enabled', self.enabled)
            # self.alarm_type = config.get('AlarmType', self.alarm_type)
            if config.get('AlarmDuration') == 0:
                self.alarm_duration = 5
            else:
                self.alarm_duration = config.get('AlarmDuration', self.alarm_duration)
            # self.alarm_duration = config.get('AlarmDuration', self.alarm_duration)
            self.enabled = config.get('AlarmEnabled', self.enabled)
            self.roi = config.get('ROI', self.roi)

            # 处理VideoOpt配置
            # video_opt = config.get('VideoOpt', {})
            # self.ratio = video_opt.get('FrameRatio', self.ratio)

            # 处理Text配置（大模型题词）
            text_config = config.get('Text', {})
            if text_config:
                self.prompt_config = text_config
                self.prompts = text_config

            yolo_config = config.get('StreamOpt', {
                'Slice': '2,2,0.2,0.2', 'FireConf': 0.8, 'PersonConf': 0.5, 'AverageSpeed': 10, 'VehicleCount': 5,
                'MotorcycleConf': 0.05
            })

            # 从顶层配置中读取 Direction，并添加到 yolo_config 中
            if 'Direction' in config:
                yolo_config['Direction'] = config['Direction']
                logger.info(f"主方向配置已读取: {config['Direction']}")

            scene_url = {
                'track_url': config.get('TrackUrl', ''),
                'detect_url': config.get('DetectUrl', ''),
                'fire_url': config.get('FireUrl', ''),
                'token_url': config.get('TokenUrl', ''),
                'label_url': config.get('LabelUrl', ''),
            }

            # 将配置传递给环境
            self.env.configure_scene(scene_url, yolo_config, occur_enable, self.alarm_duration)

            # 配置环境事件

            logger.info(f"配置加载成功: {config_path}")
            logger.info(f"媒体名称: {self.name}")
            logger.info(f"播放地址: {self.play_url}")
            logger.info(f"告警类型: {self.alarm_type}")
            logger.info(f"ROI区域: {len(self.roi)} 个")

        except FileNotFoundError:
            logger.error(f"配置文件未找到: {config_path}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON配置文件格式错误: {e}")
        except Exception as e:
            logger.error(f"加载配置文件时发生错误: {e}")

    # 配置
    def config(self, args):
        # 配置文件解析
        self.enabled = args.enabled
        self.alarm_type = args.alarm_type
        self.alarm_duration = args.alarm_duration
        self.ratio = args.ratio
        self.stcd = args.stcd
        self.roi = args.roi
        self.play_url = args.play_url

    # 使用缺省配置
    def use_default(self):
        # # 事件处理逻辑
        # self.env.register(['S行人'], Handler('行人', person_label_handler, Handler.Type.SYNC))
        # self.env.register(['S行人'], Handler('施工人员', person_label_handler, Handler.Type.SYNC))
        self.env.register(['S烟火'], Handler('烟火', fire_handler))
        # self.env.register(['S停车'], Handler('停车', None))
        self.env.register(['S物体遗留'], Handler('抛洒物', debris_handler))
        # self.env.register(['S摩托车'], Handler('摩托车', motor_label_handler, Handler.Type.SYNC))
        # self.env.register(['S逆行'], Handler('逆行', None))
        # self.env.register(['S行驶缓慢'], Handler('拥堵', None))
        self.env.register(['S浓烟'], Handler('浓烟', smoke_handler))
        self.env.register(['S火焰'], Handler('火焰', flame_handler))
        self.env.register(['S火花'], Handler('火花', spark_handler))
        # self.env.register(['S游泳'], Handler('游泳', swimming_handler))
        # self.env.register(['S人员闯入'], Handler('人员闯入', intrusion_handler))
        self.env.register(['S游泳'], Handler('游泳', None))
        self.env.register(['S人员闯入'], Handler('人员闯入', None))
        self.env.register(['S漏水'], Handler('漏水', water_leak_handler))
        self.env.register(['S漏油'], Handler('漏油', oil_leak_handler))
        self.env.register(['S漂浮物'], Handler('漂浮物', floating_debris_handler))

    def use_track_only(self):
        # 事件处理逻辑
        self.env.register(['S停车'], Handler('停车', None))
        self.env.register(['S逆行'], Handler('逆行', None))
        self.env.register(['S行驶缓慢'], Handler('拥堵', None))

    def use_image_only(self):
        # 事件处理逻辑
        self.env.register(['S行人'], Handler('行人', person_label_handler, Handler.Type.SYNC))
        self.env.register(['S行人'], Handler('施工人员', person_label_handler, Handler.Type.SYNC))
        self.env.register(['S烟火'], Handler('烟火', fire_handler))
        self.env.register(['S物体遗留'], Handler('抛洒物', debris_handler))
        self.env.register(['S摩托车'], Handler('摩托车', motor_label_handler, Handler.Type.SYNC))
        self.env.register(['S浓烟'], Handler('浓烟', smoke_handler))
        self.env.register(['S火焰'], Handler('火焰', flame_handler))
        self.env.register(['S火花'], Handler('火花', spark_handler))
        self.env.register(['S游泳'], Handler('游泳', swimming_handler))
        self.env.register(['S人员闯入'], Handler('人员闯入', intrusion_handler))
        self.env.register(['S漏水'], Handler('漏水', water_leak_handler))
        self.env.register(['S漏油'], Handler('漏油', oil_leak_handler))
        self.env.register(['S漂浮物'], Handler('漂浮物', floating_debris_handler))

    def use_config(self):
        # 事件处理逻辑
        for occur, enable in self.env.occur_enabled().items():
            logger.debug(f"occur{occur},enable{enable}")
            if enable:
                if occur == '浓烟':
                    self.env.register(['S浓烟'], Handler('浓烟', smoke_handler))
                elif occur == '火焰':
                    self.env.register(['S火焰'], Handler('火焰', flame_handler))
                elif occur == '火花':
                    self.env.register(['S火花'], Handler('火花', spark_handler))
                elif occur == '游泳':
                    self.env.register(['S游泳'], Handler('游泳', swimming_handler))
                elif occur == '人员闯入':
                    self.env.register(['S人员闯入'], Handler('人员闯入', None))
                elif occur == '漏水':
                    self.env.register(['S漏水'], Handler('漏水', water_leak_handler))
                elif occur == '漏油':
                    self.env.register(['S漏油'], Handler('漏油', oil_leak_handler))
                elif occur == '漂浮物':
                    self.env.register(['S漂浮物'], Handler('漂浮物', floating_debris_handler))
                elif occur == '高温':
                    self.env.register(['S高温'], Handler('高温', None))

    # 上报告警事件
    async def push_alarm(self, stcd, device, event, frame, boxes=None):
        logger.info(f"push alarm {stcd} {device} {event}")

        # 告警抑制逻辑
        alarm_key = f"{stcd}_{device}_{event}"
        now = time.time()

        # 检查是否在抑制时间内
        if alarm_key in self._alarm_stat:
            last_time = self._alarm_stat[alarm_key]
            if now - last_time < self.alarm_duration * 60:
                logger.info(f"告警抑制: {event} 在 {self.alarm_duration} 分钟内已上报过，跳过本次上报")
                return

        dim = get_jpeg_dimensions(frame.data())
        if dim is None:
            return
        camera_string = self.camera.replace('+', '') + '_' + event + '_' + self.name

        data = {
            'Stcd': stcd,
            # 'Stcd': '1001',
            'Device': device,
            'Camera': camera_string,
            'AlarmType': event,
            'Data': file2base64(data=frame.data()),
            'Occur': frame.occur(),
            'Result': {
                'Files': [{
                    'Width': dim[0],
                    'Height': dim[1],
                    'Regions': [

                    ],
                }]
            },
        }
        if boxes is not None:
            for box in boxes:
                region_data = {
                    # 注意：这里 Score 最好填 conf * 100，如前一个回答所述。
                    # 假设 box 是 [x_min, y_min, x_max, y_max, conf]
                    # 如果 box 只有 [x_min, y_min, x_max, y_max] 四个值，则 conf 需要从其他地方获取
                    'Score': 1.0,  # 暂时保持为 1.0
                    'Label': event,  # 类别标签
                    'Rectangle': box  # 比例坐标
                }

                data['Result']['Files'][0]['Regions'].append(region_data)

        ret = await async_http_post(self.alarm_url, json=data, headers={"Content-Type": "application/json"}, timeout=5)
        logger.debug(f'got response:{ret}')

        # 更新上报时间
        self._alarm_stat[alarm_key] = now

        return

    def _prepare_alarm_data(self, event, result, frames):
        """
        准备告警数据，处理不同事件类型的边界框和帧数据
        
        Args:
            event: 事件类型
            result: 检测结果对象
            frames: 帧列表
            
        Returns:
            tuple: (boxes列表, frame对象)
        """
        boxes = []
        frame = frames[-1]
        logger.debug(f"event{event}")
        # 处理停车、逆行、拥堵事件
        if event in ['停车', '逆行']:
            objects = result.GetObjects('停车')

            dim = get_jpeg_dimensions(frames[-1].data())
            stitch_height = dim[1] * 5  # 照片高度是5倍

            for obj in objects:
                if obj is not None:
                    box = obj.rectangle()
                    if box is not None:
                        xmin, ymin, xmax, ymax = box
                        # 原本的框y坐标
                        o_ymin = ymin * dim[1]
                        o_ymax = ymax * dim[1]
                        # 拼接后的框y坐标
                        s_ymin = o_ymin + dim[1] * 4
                        s_ymax = o_ymax + dim[1] * 4
                        # 转为比例坐标
                        s_ymin = s_ymin / stitch_height
                        s_ymax = s_ymax / stitch_height
                        # 边界检查
                        if s_ymin < 0:
                            s_ymin = 0
                        if s_ymax > stitch_height:
                            s_ymax = stitch_height

                        boxes.append([xmin, s_ymin, xmax, s_ymax])

            # 拼接图像
            frame = stitch_images([e.dict()["image"] for e in frames])
            # logger.info(f"frame{frame.dict()}")
        # 处理摩托车、行人、施工人员事件
        if event in ['摩托车', '行人', '施工人员', '拥堵', '人员闯入']:
            if event == '摩托车':
                objs = result.GetObjects('motorcycle')
            elif event in ['行人', '施工人员', '人员闯入']:
                objs = result.GetObjects('person')
            else:
                objs = []

            for obj in objs:
                if obj is not None:
                    box = obj.rectangle()
                    if box is not None:
                        xmin, ymin, xmax, ymax = box
                        boxes.append([xmin, ymin, xmax, ymax])
        if event in ['浓烟', '火焰', '火花', '游泳']:
            label_map = {'浓烟': 'smoke', '火焰': 'flame', '火花': 'spark', '游泳': 'swimming'}
            objs = result.GetObjects(label_map.get(event, ''))
            for obj in objs:
                if obj is not None:
                    box = obj.rectangle()
                    if box is not None:
                        xmin, ymin, xmax, ymax = box
                        boxes.append([xmin, ymin, xmax, ymax])

        return boxes, frame

    async def _process(self, name=None, i=0, filepath=None, img64=None, frames=None, prompt_config=None, result=None,
                       event_handler=None):
        # 调用大模型处理函数进行复核
        logger.info(f'llm process start with: {result.Labels()}')
        await self.env.llmprocess(name=name, frame=frames[-1], result=result, env=self.env)
        logger.info(f'llm process done  with: {result.Labels()}')
        if event_handler is not None:
            event_handler(name=name, result=result)
        self.env.store(result)
        # print("上报警发送前",self.enabled,self.alarm_url)
        # 根据result上报告警
        if self.enabled and self.alarm_url != '':

            for event, ok in result.Labels().items():
                boxes, frame = self._prepare_alarm_data(event, result, frames)

                if ok and frame is not None:
                    stcd = self.stcd
                    device = self.device

                    asyncio.create_task(
                        self.push_alarm(stcd, device, event, frame, boxes)
                    )

    # 处理视频流
    async def Do(self, occur_handler=None, event_handler=None):
        logger.info('stream start')

        if self.is_image() is False:
            # 启动ffmpeg持续采集图像
            self.ffmpeg = Ffmpeg()

            asyncio.create_task(
                self.ffmpeg.run(self.play_url)
            )
        frame_index = 0

        if self.env.occur_enabled().get("高温", False):
            # 启动端口
            asyncio.create_task(self.env.run_server())

        while True:

            # 小模型识别
            if self.is_image():
                frame = Frame()
                frame.read(filepath=self.play_url)
                frames = [frame]  # 原始帧
            else:
                frames = await self.ffmpeg.get_all()

                if len(frames) > 0:
                    frame = frames[-1]
                    if frame.index() == frame_index:
                        await asyncio.sleep(1)
                        continue
                    else:
                        frame_index = frame.index()

                if self.ffmpeg.status() == 0:
                    while True:
                        print(self.env.done())
                        if self.env.done():
                            break
                        else:
                            print('env task is busy.')
                            await asyncio.sleep(1)
                    break

            events = None
            detect_occurs = set()
            track_occurs, car_trace = await self.env.track(frames, self.roi, self.env.occur_enabled())
            if len(frames) > 0:
                detect_occurs, objects = await self.env.detect(frames[-1], self.roi, self.env.occur_enabled())
                occurs = detect_occurs | track_occurs

                occurs = ['S' + occur for occur in occurs]
                logger.debug(f"occurs{occurs}")
                logger.debug(f"objects{objects}")
                if occur_handler is not None:
                    occur_handler(occurs)
                events = self.env.occur2event(occurs)
                logger.debug(f'events:{events}')

                # 初始化result
                result = Result()
                # 创建任务进行大模型复核
                if events is not None and len(events) > 0:

                    # 先设置事件为True，再进行复核
                    for ev in events:
                        result.AddLabel(ev, True)

                    if '浓烟' in events and len(objects) > 0:
                        for e in objects:
                            if e['class_name'] in ['smoke', 'Smoke']:
                                xmin, ymin, xmax, ymax = e['bbox']
                                result.AddObject(Object(label='smoke', xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
                    if '火焰' in events and len(objects) > 0:
                        for e in objects:
                            if e['class_name'] in ['fire']:
                                xmin, ymin, xmax, ymax = e['bbox']
                                result.AddObject(Object(label='flame', xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
                    if '火花' in events and len(objects) > 0:
                        for e in objects:
                            if e['class_name'] in ['fire ']:
                                xmin, ymin, xmax, ymax = e['bbox']
                                result.AddObject(Object(label='spark', xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
                    if '游泳' in events and len(objects) > 0:
                        for e in objects:
                            if e['class_name'] in ['person']:
                                xmin, ymin, xmax, ymax = e['bbox']
                                result.AddObject(Object(label='swimming', xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
                    if '人员闯入' in events and len(objects) > 0:
                        logger.debug("'人员闯入' in events and len(objects) > 0:")
                        for e in objects:
                            if e['class_name'] == 'person' and e['confidence'] > 0.5:
                                xmin, ymin, xmax, ymax = e['bbox']
                                result.AddObject(Object(label='person', xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
                    if '高温' in events:
                        # 高温告警 是双光摄像头的上来的，不用小模型的结果画框
                        result.AddObject(Object(label='hot'))

                # 直接处理
                if len(frames) > 0:
                    await self.env.process(name=self.play_url, frame=frames[-1], result=result, env=self.env)

                    # 创建任务进行大模型复核
                    if self.env.has_async_events(result=result) and self.env.done():
                        self.env.create_task(self._process(
                            name=self.play_url, frames=frames, prompt_config=self.prompt_config, result=result,
                            event_handler=event_handler))
                    else:
                        # print('env task is busy.')
                        # 大模型正忙不能进行处理,清除大模型需要处理的事件,避免误报
                        self.env.llm_event_reset(result=result)
                        if event_handler is not None:
                            event_handler(name=self.play_url, result=result)
                        self.env.store(result)

                        if self.enabled and self.alarm_url != '':
                            # 收集所有告警上报任务
                            alarm_tasks = []
                            for event, ok in result.Labels().items():
                                boxes, frame = self._prepare_alarm_data(event, result, frames)

                                if ok and frame is not None:
                                    stcd = self.stcd
                                    device = self.device
                                    await self.push_alarm(stcd, device, event, frame, boxes)
                                    # 创建任务并收集
                                    # task = asyncio.create_task(
                                    #     self.push_alarm(stcd, device, event, frame, boxes)
                                    # )
                                    # alarm_tasks.append(task)

                            # 等待所有告警上报任务完成
                            # if alarm_tasks:
                            #     await asyncio.gather(*alarm_tasks, return_exceptions=True)

            if self.is_image():
                if self.env.done():
                    return
                # 等待任务执行完成
                await self.env._task
                return

            await asyncio.sleep(1)


async def push_alarm_task():
    task = asyncio.create_task(test_push_alarm())
    while True:
        if task.done():
            logger.info('task done.')
        await asyncio.sleep(1)


async def test_push_alarm():
    data = {
        'Stcd': '1001',
        'Device': 'task-id-batch-id',
        'Camera': 'xz100m',
        'AlarmType': '行人',
        'Data': file2base64(filepath='./motorbike/0001.jpg'),
        'Occur': '2025-10-20 10:00:00',
        'Result': {
            'Files': [{
                'Width': 100,
                'Height': 100,
                'Regions': [
                    {
                        'Score': 0.9,
                        'Label': '行人',
                        'Rectangle': [2, 3, 4, 5]
                    }
                ],

            }]
        },
    }

    logger.debug(f"test push alarm data: {data}")
    ret = await async_http_post("http://192.168.1.138:3004/xzhydro/api/alarm/push", json=data,
                                headers={"Content-Type": "application/json"})
    logger.info('got response')
    logger.debug(f"response: {ret}")
    return


if __name__ == '__main__':

    # asyncio.run(push_alarm_task())

    # 读取命令行参数并进行配置
    parser = argparse.ArgumentParser(description='视频流处理程序')
    parser.add_argument('--config', '-c', type=str, help='配置文件路径 (JSON格式)')
    parser.add_argument('--name', '-n', type=str, default='摄像头1.56', help='摄像头名称')
    parser.add_argument('--log-level', '-l', type=str, default='DEBUG',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='日志级别 (默认: INFO)')

    args = parser.parse_args()

    # 如果没有提供配置文件，使用默认配置
    if args.config:
        logger.info(f"使用配置文件: {args.config}")
        logger.info(f"使用摄像头名称: {args.name}")
        client = Stream(name=args.name, config_path=args.config, log_level=args.log_level)
        client.use_config()
        # client.use_default()
    else:
        logger.info("使用默认配置")
        client = Stream(name=args.name, config_path=args.config, log_level=args.log_level)
        client.use_config()

        # 默认配置
        play_url = 'rtsp://admin:Xiezuo01@192.168.1.56'
        name = '摄像头1.56'
        events = []
        client = Stream(args.name, log_level=args.log_level)
        client.play_url = play_url
        client.use_image_only()

    asyncio.run(client.Do())

    # while True:
    #     print("stream")
    #     time.sleep(1)
