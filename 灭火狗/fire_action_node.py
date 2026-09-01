#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
import os
from tool.srv import Invoke, InvokeResponse
from fire.fire_match import FireTemplateMatcher  

class ActionInvoker:
    def __init__(self):
        rospy.init_node('fire_action_node')
        
        # 初始化火情模板匹配对象
        self.fire_matcher = FireTemplateMatcher()

        # 开启服务
        self.service = rospy.Service('fire_action', Invoke, self.handle_request)
        rospy.loginfo("火情匹配服务已启动：等待 start / stop / status 指令")

    def handle_request(self, req):
        cmd = req.request
        rospy.loginfo(f"收到火情服务请求：{cmd}")

        # 启动匹配
        if cmd == "start":
            if not self.fire_matcher.running:
                self.fire_matcher.start()
                rospy.loginfo("已启动火情模板匹配")
                return InvokeResponse("ok")
            else:
                rospy.loginfo("火情匹配已经在运行中")
                return InvokeResponse("already start")

        # 停止匹配
        elif cmd == "stop":
            if self.fire_matcher.running:
                self.fire_matcher.stop()
                rospy.loginfo("已停止火情模板匹配")
                return InvokeResponse("ok")
            else:
                rospy.loginfo("火情匹配已经停止")
                return InvokeResponse("already stop")

        # 查询状态
        elif cmd == "status":
                status = self.fire_matcher.get_status()
                rospy.loginfo(f"火情匹配当前状态：{status}")
                return InvokeResponse(status)

        # 未知指令
        else:
            rospy.logwarn(f"未知指令：{cmd}")
            return InvokeResponse("error: unknown command")

    def run(self):
        rospy.spin()

if __name__ == "__main__":
    try:
        os.environ['ROS_MASTER_URI'] = 'http://192.168.123.165:11311'
        os.environ['ROS_IP'] = '192.168.123.165'  
        server = ActionInvoker()
        server.run()
    except rospy.ROSInterruptException:
        pass