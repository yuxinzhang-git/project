#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import json
import base64
import cv2
import numpy as np
import os
from datetime import datetime
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from geometry_msgs.msg import PointStamped
import paho.mqtt.client as mqtt
import math
import tf

# ------------------- 配置 -------------------
BROKER_IP = "192.168.123.164"
MQTT_TOPIC = "mqtt/face/1033360/Snap"
SAVE_DIR = "/opt/share/xzros/src/fire/fire_templates"
os.makedirs(SAVE_DIR, exist_ok=True)
TARGET_OPERATORS = ["FireSmokeSnapPush"]

FRAMES_TO_COLLECT = 5
MATCH_THRESHOLD = 0.22

# 相机内参
FX = 644.190154
FY = 643.283997
CX = 649.584230
CY = 368.422181

# ------------------- 封装后的主类 -------------------
class FireTemplateMatcher:
    def __init__(self):
        # 运行状态标记
        self.running = False
        
        self.bridge = CvBridge()
        self.color_img = None
        self.depth_img = None
        self.depth_scale = 0.001
        self.fire_template = None

        # 多帧采集
        self.collecting = False
        self.frame_buffer = []
        self.template_loaded = False

        # 相机订阅（延迟创建，避免重复订阅）
        self.color_sub = None
        self.depth_sub = None

        # 发布 /clicked_point
        self.pub_clicked_point = rospy.Publisher("/clicked_point", PointStamped, queue_size=10)
        self.listener = tf.TransformListener()
        rospy.sleep(0.5)

        # MQTT
        self.mqtt_client = None

    # ------------------- 启动方法 -------------------
    def start(self):
        if self.running:
            return
        
        self.running = True
        rospy.loginfo("[FireMatcher] 启动火情模板匹配服务")
        
        # 订阅相机
        self.color_sub = rospy.Subscriber("/camera/color/image_raw", Image, self.color_cb)
        self.depth_sub = rospy.Subscriber("/camera/aligned_depth_to_color/image_raw", Image, self.depth_cb)

        # 初始化MQTT
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_message = self.mqtt_cb
        self.mqtt_client.connect(BROKER_IP, 1883, 60)
        self.mqtt_client.loop_start()
        self.mqtt_client.subscribe(MQTT_TOPIC, 0)

    # ------------------- 停止方法 -------------------
    def stop(self):
        if not self.running:
            return
        
        self.running = False
        rospy.loginfo("[FireMatcher] 停止火情模板匹配服务")
        
        # 取消相机订阅
        if self.color_sub:
            self.color_sub.unregister()
        if self.depth_sub:
            self.depth_sub.unregister()
        
        # 关闭MQTT
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        
        # 重置状态
        self.reset()

    # ------------------- 获取状态 -------------------
    def get_status(self):
        if self.running:
            return "running"
        else:
            return "stopped"

    # ------------------- 彩色图回调 -------------------
    def color_cb(self, msg):
        if not self.running:
            return
        try:
            self.color_img = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            if self.collecting:
                self.try_match()
        except Exception as e:
            rospy.logerr(f"color_cb err: {e}")

    # ------------------- 深度图回调 -------------------
    def depth_cb(self, msg):
        if not self.running:
            return
        try:
            self.depth_img = self.bridge.imgmsg_to_cv2(msg, "passthrough")
        except:
            pass

    # ------------------- MQTT 接收模板 -------------------
    def mqtt_cb(self, client, topic, payload, qos=None):
        if not self.running or self.template_loaded:
            return
        try:
            data = json.loads(payload.payload.decode())
            op = data.get("operator")
            pic = data.get("info", {}).get("pic", "")

            if op not in TARGET_OPERATORS or not pic:
                return

            if "data:image" in pic:
                pic = pic.split(",")[1]

            img_data = base64.b64decode(pic)
            arr = np.frombuffer(img_data, np.uint8)
            self.fire_template = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if self.fire_template is not None:
                self.template_loaded = True
                self.collecting = True
                self.frame_buffer = []
                rospy.loginfo("\n火情模板已加载，开始采集5帧...")
        except:
            pass

    # ------------------- 逐帧匹配 -------------------
    def try_match(self):
        if not self.collecting:
            return
        if self.color_img is None or self.depth_img is None or self.fire_template is None:
            return

        bbox, draw_img, score, uv = self.template_match(self.color_img, self.fire_template)
        if not bbox or draw_img is None:
            return

        depth = self.get_depth(bbox)
        if not depth:
            return

        u, v = uv
        cv2.circle(draw_img, (u, v), 8, (0, 0, 255), -1)

        frame_idx = len(self.frame_buffer) + 1
        save_path = os.path.join(SAVE_DIR, f"frame_{frame_idx}_{datetime.now().strftime('%m%d%H%M%S')}.png")
        cv2.imwrite(save_path, draw_img)
        rospy.loginfo(f"第 {frame_idx} 帧匹配成功")

        self.frame_buffer.append({
            "u": u, "v": v, "depth": depth
        })

        if len(self.frame_buffer) >= FRAMES_TO_COLLECT:
            self.collecting = False
            self.process_final()

    # ------------------- 模板匹配 -------------------
    def template_match(self, img, tpl):
        try:
            img_gray = cv2.cvtColor(cv2.GaussianBlur(img, (5,5), 0), cv2.COLOR_BGR2GRAY)
            tpl_gray = cv2.cvtColor(cv2.GaussianBlur(tpl, (5,5), 0), cv2.COLOR_BGR2GRAY)
            best_val, best_loc, best_w, best_h = 0, None, 0, 0

            for s in np.linspace(0.1, 0.6, 30):
                w, h = int(tpl_gray.shape[1] * s), int(tpl_gray.shape[0] * s)
                if w <= 0 or h <= 0: continue
                resized = cv2.resize(tpl_gray, (w, h))
                res = cv2.matchTemplate(img_gray, resized, cv2.TM_CCOEFF_NORMED)
                _, val, _, loc = cv2.minMaxLoc(res)
                if val > best_val:
                    best_val, best_loc, best_w, best_h = val, loc, w, h

            if best_val < MATCH_THRESHOLD:
                return None, None, 0, (0,0)

            x1, y1 = best_loc
            x2, y2 = x1 + best_w, y1 + best_h
            out = img.copy()
            cv2.rectangle(out, (x1, y1), (x2, y2), (0,255,0), 2)
            return (x1, y1, x2, y2), out, best_val, ((x1 + x2) // 2, (y1 + y2) // 2)
        except:
            return None, None, 0, (0,0)

    # ------------------- 深度计算 -------------------
    def get_depth(self, bbox):
        x1, y1, x2, y2 = bbox
        crop = self.depth_img[max(0, y1):y2, max(0, x1):x2]
        valid = crop[crop > 0]
        return np.mean(valid) * self.depth_scale if len(valid) else None

    # ------------------- 最终处理 -------------------
    def process_final(self):
        try:
            data = self.frame_buffer
            if len(data) < 3:
                rospy.logerr("有效帧不足")
                self.reset()
                return

            us = np.array([f["u"] for f in data])
            vs = np.array([f["v"] for f in data])
            ds = np.array([f["depth"] for f in data])

            mu = np.median(us)
            mv = np.median(vs)
            md = np.median(ds)

            ok = [f for f in data if abs(f["u"]-mu)<30 and abs(f["v"]-mv)<30 and abs(f["depth"]-md)<0.15]
            if len(ok) < 3:
                rospy.logerr("过滤后无效")
                self.reset()
                return

            fu = int(np.mean([f["u"] for f in ok]))
            fv = int(np.mean([f["v"] for f in ok]))
            fd = np.mean([f["depth"] for f in ok])

            X = (fu - CX) / FX * fd
            Y = (fv - CY) / FY * fd
            Z = fd

            rospy.loginfo("="*60)
            rospy.loginfo(f"深度：{fd:.2f}m")
            rospy.loginfo(f"3D坐标：X={X:.3f}  Y={Y:.3f}  Z={Z:.3f}")
            rospy.loginfo("="*60)

            point_msg = PointStamped()
            point_msg.header.frame_id = "local"
            point_msg.header.stamp = rospy.Time(0)

            point_msg.point.x = Z
            point_msg.point.y = -X
            point_msg.point.z = 0.0

            try:
                self.listener.waitForTransform("map", "local", rospy.Time(0), rospy.Duration(0.5))
                point_map = self.listener.transformPoint("map", point_msg)
                self.pub_clicked_point.publish(point_map)
                rospy.loginfo("成功发送 map 坐标系火情点到 RViz /clicked_point")
            except Exception as e:
                rospy.logerr(f"TF变换失败: {e}")
                self.pub_clicked_point.publish(point_msg)

        except Exception as e:
            rospy.logerr(f"process_final err: {e}")
        self.reset()

    # ------------------- 重置状态 -------------------
    def reset(self):
        self.collecting = False
        self.frame_buffer = []
        self.template_loaded = False
        rospy.loginfo("\n已重置，等待下一次MQTT触发...")
