#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能交通信号灯控制器
控制交通信号灯状态，实现智能配时和协调控制
"""

import carla
import time
import threading
import argparse
from enum import Enum


class LightState(Enum):
    """信号灯状态枚举"""
    RED = 0
    YELLOW = 1
    GREEN = 2


class TrafficLightController:
    """交通信号灯控制器"""
    
    def __init__(self, host='localhost', port=2000):
        """初始化信号灯控制器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.traffic_lights = []
        self.running = False
        self.control_thread = None
        print("[INFO] 交通信号灯控制器已初始化")
        
    def get_all_traffic_lights(self):
        """获取所有交通信号灯"""
        self.traffic_lights = self.world.get_actors().filter('traffic.traffic_light')
        print(f"[INFO] 发现 {len(self.traffic_lights)} 个交通信号灯")
        return self.traffic_lights
    
    def set_light_state(self, traffic_light, state, duration=None):
        """设置单个信号灯状态"""
        if state == LightState.RED:
            traffic_light.set_state(carla.TrafficLightState.Red)
            traffic_light.set_red_time(duration if duration else 30.0)
        elif state == LightState.YELLOW:
            traffic_light.set_state(carla.TrafficLightState.Yellow)
            traffic_light.set_yellow_time(duration if duration else 3.0)
        elif state == LightState.GREEN:
            traffic_light.set_state(carla.TrafficLightState.Green)
            traffic_light.set_green_time(duration if duration else 30.0)
            
    def set_all_red(self):
        """设置所有信号灯为红灯（紧急模式）"""
        for tl in self.traffic_lights:
            self.set_light_state(tl, LightState.RED)
        print("[信号灯] 所有信号灯已设置为红灯（紧急模式）")
        
    def set_all_green(self):
        """设置所有信号灯为绿灯（仅用于测试）"""
        for tl in self.traffic_lights:
            self.set_light_state(tl, LightState.GREEN)
        print("[信号灯] 所有信号灯已设置为绿灯（测试模式）")
        
    def create_coordinated_pattern(self, pattern_type='standard'):
        """创建协调控制模式"""
        if pattern_type == 'standard':
            # 标准四相位控制
            return {
                'phase1': {'green': 30, 'yellow': 3, 'red': 33},  # 南北直行
                'phase2': {'green': 30, 'yellow': 3, 'red': 33},  # 东西直行
            }
        elif pattern_type == 'rush_hour':
            # 高峰期模式
            return {
                'phase1': {'green': 45, 'yellow': 3, 'red': 28},
                'phase2': {'green': 20, 'yellow': 3, 'red': 53},
            }
        elif pattern_type == 'night':
            # 夜间模式（黄灯闪烁）
            return {
                'phase1': {'green': 0, 'yellow': 2, 'red': 0},
                'phase2': {'green': 0, 'yellow': 2, 'red': 0},
            }
        else:
            return pattern_type
    
    def coordinated_control(self, pattern='standard'):
        """协调控制所有信号灯"""
        timing = self.create_coordinated_pattern(pattern)
        self.running = True
        
        print(f"[INFO] 启动协调控制模式: {pattern}")
        
        # 将信号灯分组（假设奇偶分组）
        group1 = self.traffic_lights[::2]  # 第一组
        group2 = self.traffic_lights[1::2]  # 第二组
        
        try:
            while self.running:
                # 第一组绿灯，第二组红灯
                for tl in group1:
                    self.set_light_state(tl, LightState.GREEN, timing['phase1']['green'])
                for tl in group2:
                    self.set_light_state(tl, LightState.RED, timing['phase1']['red'])
                    
                time.sleep(timing['phase1']['green'])
                
                # 第一组黄灯
                for tl in group1:
                    self.set_light_state(tl, LightState.YELLOW, timing['phase1']['yellow'])
                time.sleep(timing['phase1']['yellow'])
                
                # 第一组红灯，第二组绿灯
                for tl in group1:
                    self.set_light_state(tl, LightState.RED, timing['phase2']['red'])
                for tl in group2:
                    self.set_light_state(tl, LightState.GREEN, timing['phase2']['green'])
                    
                time.sleep(timing['phase2']['green'])
                
                # 第二组黄灯
                for tl in group2:
                    self.set_light_state(tl, LightState.YELLOW, timing['phase2']['yellow'])
                time.sleep(timing['phase2']['yellow'])
                
        except Exception as e:
            print(f"[ERROR] 协调控制出错: {e}")
            
    def adaptive_control(self, traffic_density):
        """自适应控制（根据交通流量调整）"""
        if traffic_density > 0.8:
            # 高密度，延长绿灯时间
            pattern = 'rush_hour'
        elif traffic_density < 0.2:
            # 低密度，缩短周期
            pattern = 'night'
        else:
            pattern = 'standard'
            
        return self.create_coordinated_pattern(pattern)
    
    def pedestrian_crossing(self, duration=15):
        """行人过街模式（全红）"""
        print(f"[信号灯] 启动行人过街模式，持续时间: {duration}秒")
        self.set_all_red()
        time.sleep(duration)
        print("[信号灯] 行人过街结束，恢复正常控制")
        
    def emergency_priority(self, direction='ns'):
        """紧急车辆优先模式"""
        print(f"[信号灯] 紧急车辆优先: {direction}")
        
        if direction == 'ns':  # 南北方向
            priority_group = self.traffic_lights[::2]
            other_group = self.traffic_lights[1::2]
        else:  # 东西方向
            priority_group = self.traffic_lights[1::2]
            other_group = self.traffic_lights[::2]
            
        # 优先方向绿灯，其他方向红灯
        for tl in priority_group:
            self.set_light_state(tl, LightState.GREEN, 60)
        for tl in other_group:
            self.set_light_state(tl, LightState.RED, 60)
            
    def start_control(self, mode='standard'):
        """启动控制线程"""
        self.get_all_traffic_lights()
        
        if mode == 'coordinated':
            self.control_thread = threading.Thread(
                target=self.coordinated_control, 
                args=('standard',)
            )
        elif mode == 'adaptive':
            self.control_thread = threading.Thread(
                target=self._adaptive_control_loop
            )
            
        self.control_thread.start()
        print(f"[INFO] 已启动 {mode} 控制模式")
        
    def _adaptive_control_loop(self):
        """自适应控制循环"""
        while self.running:
            # 模拟检测交通流量
            traffic_density = self._detect_traffic_density()
            pattern = self.adaptive_control(traffic_density)
            
            print(f"[自适应] 当前交通密度: {traffic_density:.2f}, 使用模式: {pattern}")
            
            # 执行一个周期
            self.coordinated_control(pattern)
            time.sleep(1)
    
    def _detect_traffic_density(self):
        """检测交通密度（简化版）"""
        # 实际应用中应该通过传感器或摄像头检测
        # 这里返回模拟值
        import random
        return random.uniform(0.3, 0.9)
    
    def stop_control(self):
        """停止控制"""
        self.running = False
        if self.control_thread:
            self.control_thread.join()
        print("[INFO] 信号灯控制已停止")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='交通信号灯控制器')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--mode', default='coordinated',
                       choices=['coordinated', 'adaptive', 'manual'],
                       help='控制模式')
    parser.add_argument('--action', default='start',
                       choices=['start', 'emergency', 'pedestrian', 'all_red'],
                       help='执行动作')
    
    args = parser.parse_args()
    
    controller = TrafficLightController(args.host, args.port)
    
    try:
        if args.action == 'start':
            controller.start_control(args.mode)
            print("[INFO] 按 Ctrl+C 停止")
            while True:
                time.sleep(1)
        elif args.action == 'emergency':
            controller.get_all_traffic_lights()
            controller.emergency_priority('ns')
        elif args.action == 'pedestrian':
            controller.get_all_traffic_lights()
            controller.pedestrian_crossing()
        elif args.action == 'all_red':
            controller.get_all_traffic_lights()
            controller.set_all_red()
            
    except KeyboardInterrupt:
        print("\n[INFO] 程序被中断")
    finally:
        controller.stop_control()


if __name__ == '__main__':
    main()
