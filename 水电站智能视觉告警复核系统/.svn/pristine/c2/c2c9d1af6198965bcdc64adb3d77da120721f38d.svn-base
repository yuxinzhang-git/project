import numpy as np
from collections import defaultdict, deque
import requests, time
from ffmpeg import Ffmpeg
import asyncio
import uuid
import datetime
import os
import sys
import json
import logging

# 配置日志系统
logger = logging.getLogger(__name__)

output_folder = "tracked_images"
class Tracker:
    def __init__(self, url):
        """
        初始化追踪器，用于管理多个目标的运动轨迹。
        
        
        """
        self.url = url
        self.frame=[]   #存储帧数据
        self.track_history = defaultdict(deque)  # 存储每个目标的轨迹历史
        self.last_positions = {}                 # 存储每个目标在上一帧的位置
        
        # 逆行检测的配置
        
        
        
        self.TRACK_FRAME_THRESHOLD = 5
        self.count = 0

    
    async def process(self, frames):
        if len(frames) < 5:
            logger.warning("frames are not enough.")
            return None

        try:
            data = {
                'data': [e.dict() for e in frames],
            }
            # print(data)
            # if not os.path.exists(output_folder):
            #     os.makedirs(output_folder)
            #     logger.info(f"文件夹 '{output_folder}' 已创建。")
            # current_date = datetime.datetime.now()
            # filename = current_date.strftime("%Y-%m-%d_%H-%M-%S") + ".jpg"
            # full_path = os.path.join(output_folder, filename)

            # # Send the POST request
            # response2 = requests.post('http://192.168.1.65:5004/track', json=data, timeout=300)
            
            # # Check for HTTP errors
            # response2.raise_for_status()

            # # Open the file in binary write mode and save the content
            # with open(full_path, 'wb') as f:
            #     f.write(response2.content)

            # logger.info(f"文件已成功保存为 {full_path}")

            response = requests.post(self.url, json=data)
            if response.status_code == 200:
                # print("INFO: 成功接收追踪结果。", response.json())
                results = response.json()
                # detections = results[0].boxes if results[0].boxes is not None else []
                self.update(results)
                self.clean_track_history()#控制轨迹数,防止内存占用过大
                
                # 保存results到JSON文件（追加模式）
                # results_file = "tracker_results.json"
                # all_results = []
                
                # # 读取已有数据
                # if os.path.exists(results_file):
                #     try:
                #         with open(results_file, "r", encoding="utf-8") as f:
                #             all_results = json.load(f)
                #     except:
                #         all_results = []
                
                # # 追加新结果（带时间戳）
                # all_results.append({
                #     "timestamp": datetime.datetime.now().isoformat(),
                #     "results": results
                # })
                
                # # 写回文件
                # with open(results_file, "w", encoding="utf-8") as f:
                #     json.dump(all_results, f, ensure_ascii=False, indent=2)
                
                return results
            else:
                logger.error(f"Track API 请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"调用 Track API 时发生异常: {e}")
            return None

    def process_frame(self, frame):   
      
        self.frame.append(frame)
        if len(self.frame) >= self.TRACK_FRAME_THRESHOLD:
            # self.update(self.frame)
            results = self.call_api(self.frame)
            detections = results[0].boxes if results[0].boxes is not None else []
            self.update(detections)
            self.frame = []
            self.count = 0
        else:
            self.count += 1

    def update(self, detections):
        """
        用当前帧的检测结果更新所有目标的轨迹。
       
        """
        if not detections or 'trajectories' not in detections:
            logger.warning("追踪结果为空或格式不正确，跳过更新。")
            return
        
        for track_id, data in detections['trajectories'].items():
            # 修改条件：轨迹点数 >= 3 即可（原来是 > 4）
            if 'trajectory' in data and data['trajectory'] and len(data['trajectory']) >= 4:
                # 遍历轨迹中的每个点
                if data['class_name'] in ['car', 'truck', 'bus']:
                    time_based_uuid = uuid.uuid1()
                    id_string = f"{time_based_uuid}_{track_id}"
                    for point in data['trajectory']:
                        if 'center' in point and len(point['center']) == 2:
                            # 提取中心点坐标，并添加到轨迹历史中
                            self.track_history[id_string].append(point['center'])
                    
                    # 限制轨迹历史的长度，防止内存占用过大
                    while len(self.track_history[id_string]) > 30:
                        self.track_history[id_string].popleft()

    def get_tracks(self):
        """
        返回所有目标的完整轨迹历史。
        """
        return self.track_history
    def delet_tracks(self,id):
        """
        返回所有目标的完整轨迹历史。
        """
        if id in self.track_history:
            del self.track_history[id]
    
    def clean_track_history(self):
        """
        清理轨迹历史，防止内存占用过大。
        """
        for track_id in self.track_history:
            if len(self.track_history[track_id]) > 60:
                self.track_history[track_id].popleft()

async def test():
    play_url = 'person.mp4'
    track=Tracker("http://192.168.1.65:5004/track-info")
    ffmpeg = Ffmpeg()
    asyncio.create_task(
        ffmpeg.run(play_url)
    )

    while True:
        frames = await ffmpeg.get_all()
        n = len(frames)
        if n < 5:
            logger.debug(f'frames {n}')
        else:
            ts = time.time()
            results = await track.process(frames)
            elasped = time.time()-ts
            tracks=track.get_tracks()
            logger.debug("===============================")
            for  track_id, data in tracks.items():
                
                logger.debug(f"track_id{track_id},data{data}")

            # print(f"tracker elasped: {elasped}, {results}")
            

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(test())
