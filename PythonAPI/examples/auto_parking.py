#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆自动泊车系统
实现车辆的自动平行泊车和垂直泊车功能
"""

import carla
import math
import numpy as np
import time
import argparse


class AutoParking:
    """自动泊车控制器"""
    
    def __init__(self, host='localhost', port=2000):
        """初始化自动泊车系统"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.vehicle = None
        self.parking_spot = None
        print("[INFO] 自动泊车系统已初始化")
        
    def spawn_vehicle(self, transform=None):
        """生成测试车辆"""
        blueprint_library = self.world.get_blueprint_library()
        vehicle_bp = blueprint_library.filter('vehicle.tesla.model3')[0]
        
        if transform is None:
            # 默认生成位置
            transform = carla.Transform(
                carla.Location(x=50, y=10, z=0.5),
                carla.Rotation(yaw=0)
            )
            
        self.vehicle = self.world.spawn_actor(vehicle_bp, transform)
        print(f"[INFO] 车辆已生成: {self.vehicle.type_id}")
        return self.vehicle
    
    def calculate_parking_trajectory(self, start_pos, end_pos, parking_type='parallel'):
        """计算泊车轨迹"""
        trajectory = []
        
        if parking_type == 'parallel':
            # 平行泊车轨迹
            # 1. 向前行驶到泊车起点
            mid_point = carla.Location(
                x=start_pos.location.x + 5,
                y=start_pos.location.y,
                z=start_pos.location.z
            )
            trajectory.append(('drive_forward', mid_point))
            
            # 2. 倒车入库
            trajectory.append(('reverse_park', end_pos.location))
            
        elif parking_type == 'perpendicular':
            # 垂直泊车轨迹
            # 1. 向前行驶
            mid_point = carla.Location(
                x=start_pos.location.x + 3,
                y=start_pos.location.y,
                z=start_pos.location.z
            )
            trajectory.append(('drive_forward', mid_point))
            
            # 2. 转向入库
            turn_point = carla.Location(
                x=mid_point.x,
                y=end_pos.location.y,
                z=end_pos.location.z
            )
            trajectory.append(('turn_in', turn_point))
            trajectory.append(('final_adjust', end_pos.location))
            
        return trajectory
    
    def execute_parking(self, trajectory):
        """执行泊车动作"""
        if not self.vehicle:
            print("[ERROR] 未生成车辆")
            return
            
        for action, target in trajectory:
            print(f"[泊车] 执行动作: {action}")
            
            if action == 'drive_forward':
                self._drive_forward(target)
            elif action == 'reverse_park':
                self._reverse_park(target)
            elif action == 'turn_in':
                self._turn_in(target)
            elif action == 'final_adjust':
                self._final_adjust(target)
                
            time.sleep(0.5)
            
        print("[INFO] 泊车完成！")
    
    def _drive_forward(self, target):
        """向前行驶"""
        control = carla.VehicleControl()
        control.throttle = 0.3
        control.steer = 0.0
        
        current_pos = self.vehicle.get_location()
        distance = self._calculate_distance(current_pos, target)
        
        while distance > 1.0:
            self.vehicle.apply_control(control)
            time.sleep(0.05)
            current_pos = self.vehicle.get_location()
            distance = self._calculate_distance(current_pos, target)
            
        control.throttle = 0.0
        self.vehicle.apply_control(control)
    
    def _reverse_park(self, target):
        """倒车入库"""
        control = carla.VehicleControl()
        control.reverse = True
        control.throttle = 0.2
        control.steer = 0.3  # 向右打方向
        
        current_pos = self.vehicle.get_location()
        distance = self._calculate_distance(current_pos, target)
        
        while distance > 0.5:
            self.vehicle.apply_control(control)
            time.sleep(0.05)
            current_pos = self.vehicle.get_location()
            distance = self._calculate_distance(current_pos, target)
            
        control.throttle = 0.0
        self.vehicle.apply_control(control)
    
    def _turn_in(self, target):
        """转向入库"""
        control = carla.VehicleControl()
        control.throttle = 0.2
        control.steer = 0.5
        
        current_pos = self.vehicle.get_location()
        distance = self._calculate_distance(current_pos, target)
        
        while distance > 0.5:
            self.vehicle.apply_control(control)
            time.sleep(0.05)
            current_pos = self.vehicle.get_location()
            distance = self._calculate_distance(current_pos, target)
            
        control.throttle = 0.0
        self.vehicle.apply_control(control)
    
    def _final_adjust(self, target):
        """最终调整"""
        control = carla.VehicleControl()
        control.throttle = 0.1
        control.steer = 0.0
        
        current_pos = self.vehicle.get_location()
        distance = self._calculate_distance(current_pos, target)
        
        while distance > 0.2:
            if distance > 1.0:
                control.reverse = False
            else:
                control.reverse = True
                control.throttle = 0.1
                
            self.vehicle.apply_control(control)
            time.sleep(0.05)
            current_pos = self.vehicle.get_location()
            distance = self._calculate_distance(current_pos, target)
            
        control.throttle = 0.0
        control.brake = 1.0
        self.vehicle.apply_control(control)
        time.sleep(0.5)
        control.brake = 0.0
        self.vehicle.apply_control(control)
    
    def _calculate_distance(self, loc1, loc2):
        """计算两点距离"""
        return math.sqrt(
            (loc1.x - loc2.x)**2 + 
            (loc1.y - loc2.y)**2 + 
            (loc1.z - loc2.z)**2
        )
    
    def detect_parking_spot(self):
        """检测可用停车位"""
        # 简化的停车位检测逻辑
        # 实际应用中可以使用传感器数据
        parking_spots = []
        
        # 模拟检测到的停车位
        spot1 = carla.Transform(
            carla.Location(x=55, y=15, z=0),
            carla.Rotation(yaw=90)
        )
        parking_spots.append(('parallel', spot1))
        
        spot2 = carla.Transform(
            carla.Location(x=60, y=20, z=0),
            carla.Rotation(yaw=0)
        )
        parking_spots.append(('perpendicular', spot2))
        
        return parking_spots
    
    def cleanup(self):
        """清理资源"""
        if self.vehicle:
            self.vehicle.destroy()
            print("[INFO] 车辆已销毁")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动泊车系统')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--type', default='parallel', 
                       choices=['parallel', 'perpendicular'],
                       help='泊车类型')
    
    args = parser.parse_args()
    
    try:
        parking = AutoParking(args.host, args.port)
        
        # 生成车辆
        start_transform = carla.Transform(
            carla.Location(x=40, y=10, z=0.5),
            carla.Rotation(yaw=0)
        )
        parking.spawn_vehicle(start_transform)
        
        # 检测停车位
        spots = parking.detect_parking_spot()
        if spots:
            spot_type, spot_transform = spots[0]
            print(f"[INFO] 检测到停车位: {spot_type}")
            
            # 计算并执行泊车轨迹
            trajectory = parking.calculate_parking_trajectory(
                start_transform, spot_transform, args.type
            )
            parking.execute_parking(trajectory)
        else:
            print("[WARNING] 未检测到可用停车位")
            
    except KeyboardInterrupt:
        print("\n[INFO] 程序被中断")
    finally:
        if 'parking' in locals():
            parking.cleanup()


if __name__ == '__main__':
    main()
