#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆碰撞检测系统
实时检测车辆碰撞事件，记录碰撞信息并触发警报
"""

import carla
import time
import json
from datetime import datetime
import argparse
from collections import deque


class CollisionEvent:
    """碰撞事件类"""
    def __init__(self, timestamp, intensity, other_actor, location, normal_impulse):
        self.timestamp = timestamp
        self.intensity = intensity
        self.other_actor = other_actor
        self.location = location
        self.normal_impulse = normal_impulse
        self.time_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


class CollisionDetector:
    """碰撞检测器"""
    
    def __init__(self, host='localhost', port=2000):
        """初始化碰撞检测器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        
        self.vehicle = None
        self.collision_sensor = None
        self.collision_history = deque(maxlen=100)
        self.collision_count = 0
        self.total_impulse = 0.0
        
        self.on_collision_callback = None
        
        print("[INFO] 碰撞检测系统已初始化")
        
    def attach_to_vehicle(self, vehicle):
        """附加碰撞传感器到车辆"""
        self.vehicle = vehicle
        
        # 创建碰撞传感器
        blueprint_library = self.world.get_blueprint_library()
        collision_bp = blueprint_library.find('sensor.other.collision')
        
        collision_transform = carla.Transform()
        self.collision_sensor = self.world.spawn_actor(
            collision_bp,
            collision_transform,
            attach_to=vehicle
        )
        
        # 设置碰撞回调
        self.collision_sensor.listen(lambda event: self._on_collision(event))
        
        print(f"[INFO] 碰撞传感器已附加到车辆 {vehicle.id}")
        
    def _on_collision(self, event):
        """碰撞事件回调"""
        # 获取碰撞信息
        actor = event.actor
        other_actor = event.other_actor
        impulse = event.normal_impulse
        intensity = math.sqrt(impulse.x**2 + impulse.y**2 + impulse.z**2)
        
        # 创建碰撞事件
        collision_event = CollisionEvent(
            timestamp=time.time(),
            intensity=intensity,
            other_actor=other_actor.type_id if other_actor else None,
            location=actor.get_location(),
            normal_impulse=impulse
        )
        
        self.collision_history.append(collision_event)
        self.collision_count += 1
        self.total_impulse += intensity
        
        # 打印碰撞信息
        self._print_collision_info(collision_event)
        
        # 触发警报
        self._trigger_alert(collision_event)
        
        # 执行用户回调
        if self.on_collision_callback:
            self.on_collision_callback(collision_event)
            
    def _print_collision_info(self, event):
        """打印碰撞信息"""
        severity = self._get_severity(event.intensity)
        
        print("\n" + "="*50)
        print("⚠️  碰撞检测！")
        print("="*50)
        print(f"时间: {event.time_str}")
        print(f"严重程度: {severity}")
        print(f"碰撞强度: {event.intensity:.2f} N·s")
        print(f"碰撞对象: {event.other_actor or '未知'}")
        print(f"位置: ({event.location.x:.2f}, {event.location.y:.2f}, {event.location.z:.2f})")
        print("="*50 + "\n")
        
    def _get_severity(self, intensity):
        """获取碰撞严重程度"""
        if intensity < 100:
            return "轻微 🟢"
        elif intensity < 500:
            return "中等 🟡"
        elif intensity < 1000:
            return "严重 🟠"
        else:
            return "致命 🔴"
            
    def _trigger_alert(self, event):
        """触发碰撞警报"""
        severity = self._get_severity(event.intensity)
        
        # 在模拟器中显示警报
        if self.world:
            # 在车辆位置显示警报文字
            alert_location = event.location + carla.Location(z=2.0)
            self.world.debug.draw_string(
                alert_location,
                f"COLLISION! {severity}",
                color=carla.Color(255, 0, 0),
                life_time=5.0
            )
            
            # 绘制碰撞点
            self.world.debug.draw_point(
                event.location,
                size=0.3,
                color=carla.Color(255, 0, 0),
                life_time=10.0
            )
            
    def set_collision_callback(self, callback):
        """设置碰撞回调函数"""
        self.on_collision_callback = callback
        
    def get_collision_report(self):
        """获取碰撞报告"""
        if not self.collision_history:
            return "无碰撞记录"
            
        report = {
            'total_collisions': self.collision_count,
            'total_impulse': self.total_impulse,
            'average_intensity': self.total_impulse / self.collision_count if self.collision_count > 0 else 0,
            'collisions': []
        }
        
        for i, event in enumerate(self.collision_history, 1):
            report['collisions'].append({
                'index': i,
                'time': event.time_str,
                'intensity': round(event.intensity, 2),
                'severity': self._get_severity(event.intensity),
                'other_actor': event.other_actor,
                'location': {
                    'x': round(event.location.x, 2),
                    'y': round(event.location.y, 2),
                    'z': round(event.location.z, 2)
                }
            })
            
        return report
        
    def save_report(self, filename=None):
        """保存碰撞报告到文件"""
        if not filename:
            filename = f'collision_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
        report = self.get_collision_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"[INFO] 碰撞报告已保存到: {filename}")
        return filename
        
    def print_summary(self):
        """打印碰撞摘要"""
        print("\n" + "="*50)
        print("碰撞检测摘要")
        print("="*50)
        print(f"总碰撞次数: {self.collision_count}")
        print(f"总冲量: {self.total_impulse:.2f} N·s")
        
        if self.collision_count > 0:
            avg_intensity = self.total_impulse / self.collision_count
            print(f"平均碰撞强度: {avg_intensity:.2f} N·s")
            
            # 统计严重程度
            severity_counts = {'轻微 🟢': 0, '中等 🟡': 0, '严重 🟠': 0, '致命 🔴': 0}
            for event in self.collision_history:
                severity = self._get_severity(event.intensity)
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
            print("\n严重程度分布:")
            for severity, count in severity_counts.items():
                if count > 0:
                    print(f"  {severity}: {count} 次")
                    
        print("="*50 + "\n")
        
    def reset(self):
        """重置碰撞统计"""
        self.collision_history.clear()
        self.collision_count = 0
        self.total_impulse = 0.0
        print("[INFO] 碰撞统计已重置")
        
    def cleanup(self):
        """清理资源"""
        if self.collision_sensor:
            self.collision_sensor.stop()
            self.collision_sensor.destroy()
        print("[INFO] 碰撞检测资源已清理")


import math


class SafetyMonitor:
    """安全监控器"""
    
    def __init__(self, world):
        """初始化安全监控器"""
        self.world = world
        self.min_safe_distance = 5.0  # 最小安全距离（米）
        self.speed_limit = 50.0  # 速度限制（km/h）
        
    def check_safe_distance(self, vehicle):
        """检查与前车的安全距离"""
        vehicle_location = vehicle.get_location()
        vehicle_velocity = vehicle.get_velocity()
        vehicle_speed = 3.6 * math.sqrt(vehicle_velocity.x**2 + vehicle_velocity.y**2 + vehicle_velocity.z**2)
        
        # 获取前方车辆
        actors = self.world.get_actors().filter('vehicle.*')
        min_distance = float('inf')
        front_vehicle = None
        
        for actor in actors:
            if actor.id == vehicle.id:
                continue
                
            actor_location = actor.get_location()
            distance = vehicle_location.distance(actor_location)
            
            # 检查是否在前方
            direction = carla.Vector3D(
                actor_location.x - vehicle_location.x,
                actor_location.y - vehicle_location.y,
                0
            )
            
            # 简化的前方检测
            if distance < min_distance and distance < 50:  # 只检查50米内的
                min_distance = distance
                front_vehicle = actor
                
        # 计算安全距离（基于速度）
        safe_distance = max(self.min_safe_distance, vehicle_speed * 0.5)
        
        if min_distance < safe_distance:
            return {
                'safe': False,
                'distance': min_distance,
                'safe_distance': safe_distance,
                'front_vehicle': front_vehicle.type_id if front_vehicle else None
            }
        else:
            return {
                'safe': True,
                'distance': min_distance,
                'safe_distance': safe_distance
            }
            
    def check_speed_limit(self, vehicle):
        """检查是否超速"""
        velocity = vehicle.get_velocity()
        speed = 3.6 * math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
        
        return {
            'speed': speed,
            'limit': self.speed_limit,
            'exceeded': speed > self.speed_limit,
            'excess': max(0, speed - self.speed_limit)
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='车辆碰撞检测系统')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--duration', type=int, default=60, help='监控时长(秒)')
    
    args = parser.parse_args()
    
    detector = CollisionDetector(args.host, args.port)
    
    try:
        # 获取车辆
        vehicles = detector.world.get_actors().filter('vehicle.*')
        if vehicles:
            vehicle = vehicles[0]
            detector.attach_to_vehicle(vehicle)
            
            # 创建安全监控器
            safety = SafetyMonitor(detector.world)
            
            print(f"[INFO] 开始监控车辆 {vehicle.id}，持续 {args.duration} 秒")
            print("[INFO] 按 Ctrl+C 停止")
            
            start_time = time.time()
            while time.time() - start_time < args.duration:
                # 检查安全距离
                distance_check = safety.check_safe_distance(vehicle)
                if not distance_check['safe']:
                    print(f"[WARNING] 距离前车过近: {distance_check['distance']:.2f}m "
                          f"(安全距离: {distance_check['safe_distance']:.2f}m)")
                    
                # 检查速度
                speed_check = safety.check_speed_limit(vehicle)
                if speed_check['exceeded']:
                    print(f"[WARNING] 超速: {speed_check['speed']:.1f}km/h "
                          f"(限速: {speed_check['limit']:.1f}km/h)")
                    
                time.sleep(1)
                
        else:
            print("[WARNING] 未找到车辆")
            
    except KeyboardInterrupt:
        print("\n[INFO] 监控被中断")
    finally:
        detector.print_summary()
        detector.save_report()
        detector.cleanup()


if __name__ == '__main__':
    main()
