#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据记录与分析模块
记录模拟器中的车辆、传感器数据，并进行分析
"""

import carla
import json
import csv
import time
import os
from datetime import datetime
import argparse
import threading


class DataRecorder:
    """数据记录器"""
    
    def __init__(self, host='localhost', port=2000, output_dir='./recordings'):
        """初始化数据记录器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.output_dir = output_dir
        self.recording = False
        self.recorded_data = []
        self.sensors = []
        self.vehicles = []
        self.record_thread = None
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        print(f"[INFO] 数据记录器已初始化，输出目录: {output_dir}")
        
    def attach_camera(self, vehicle, camera_type='rgb'):
        """为车辆附加摄像头"""
        blueprint_library = self.world.get_blueprint_library()
        
        if camera_type == 'rgb':
            camera_bp = blueprint_library.find('sensor.camera.rgb')
        elif camera_type == 'depth':
            camera_bp = blueprint_library.find('sensor.camera.depth')
        elif camera_type == 'semantic':
            camera_bp = blueprint_library.find('sensor.camera.semantic_segmentation')
        else:
            camera_bp = blueprint_library.find('sensor.camera.rgb')
            
        camera_bp.set_attribute('image_size_x', '800')
        camera_bp.set_attribute('image_size_y', '600')
        camera_bp.set_attribute('fov', '110')
        
        # 设置摄像头位置（车辆前方）
        camera_transform = carla.Transform(
            carla.Location(x=1.6, z=1.7)
        )
        
        camera = self.world.spawn_actor(
            camera_bp, 
            camera_transform, 
            attach_to=vehicle
        )
        
        # 设置图像保存回调
        output_path = os.path.join(self.output_dir, f'camera_{camera_type}_{int(time.time())}')
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        camera.listen(lambda image: image.save_to_disk(
            os.path.join(output_path, f'{image.frame:06d}.png')
        ))
        
        self.sensors.append(camera)
        print(f"[INFO] 已附加 {camera_type} 摄像头到车辆")
        return camera
    
    def attach_lidar(self, vehicle):
        """为车辆附加激光雷达"""
        blueprint_library = self.world.get_blueprint_library()
        lidar_bp = blueprint_library.find('sensor.lidar.ray_cast')
        
        lidar_bp.set_attribute('range', '50')
        lidar_bp.set_attribute('rotation_frequency', '10')
        lidar_bp.set_attribute('channels', '32')
        lidar_bp.set_attribute('points_per_second', '56000')
        
        lidar_transform = carla.Transform(carla.Location(x=0, z=2.4))
        lidar = self.world.spawn_actor(
            lidar_bp,
            lidar_transform,
            attach_to=vehicle
        )
        
        # 保存点云数据
        output_path = os.path.join(self.output_dir, f'lidar_{int(time.time())}')
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        lidar.listen(lambda data: data.save_to_disk(
            os.path.join(output_path, f'{data.frame:06d}.ply')
        ))
        
        self.sensors.append(lidar)
        print("[INFO] 已附加激光雷达到车辆")
        return lidar
    
    def attach_gnss(self, vehicle):
        """为车辆附加GNSS传感器"""
        blueprint_library = self.world.get_blueprint_library()
        gnss_bp = blueprint_library.find('sensor.other.gnss')
        
        gnss_transform = carla.Transform(carla.Location(x=0, z=2.0))
        gnss = self.world.spawn_actor(
            gnss_bp,
            gnss_transform,
            attach_to=vehicle
        )
        
        gnss.listen(lambda data: self._record_gnss_data(data))
        self.sensors.append(gnss)
        print("[INFO] 已附加GNSS到车辆")
        return gnss
    
    def attach_imu(self, vehicle):
        """为车辆附加IMU传感器"""
        blueprint_library = self.world.get_blueprint_library()
        imu_bp = blueprint_library.find('sensor.other.imu')
        
        imu_transform = carla.Transform(carla.Location(x=0, z=2.0))
        imu = self.world.spawn_actor(
            imu_bp,
            imu_transform,
            attach_to=vehicle
        )
        
        imu.listen(lambda data: self._record_imu_data(data))
        self.sensors.append(imu)
        print("[INFO] 已附加IMU到车辆")
        return imu
    
    def _record_gnss_data(self, data):
        """记录GNSS数据"""
        if self.recording:
            self.recorded_data.append({
                'timestamp': data.timestamp,
                'type': 'gnss',
                'latitude': data.latitude,
                'longitude': data.longitude,
                'altitude': data.altitude
            })
    
    def _record_imu_data(self, data):
        """记录IMU数据"""
        if self.recording:
            self.recorded_data.append({
                'timestamp': data.timestamp,
                'type': 'imu',
                'accelerometer': {
                    'x': data.accelerometer.x,
                    'y': data.accelerometer.y,
                    'z': data.accelerometer.z
                },
                'gyroscope': {
                    'x': data.gyroscope.x,
                    'y': data.gyroscope.y,
                    'z': data.gyroscope.z
                },
                'compass': data.compass
            })
    
    def start_recording(self, duration=None):
        """开始记录"""
        self.recording = True
        self.recorded_data = []
        self.start_time = time.time()
        
        print(f"[INFO] 开始记录数据...")
        if duration:
            print(f"[INFO] 记录时长: {duration} 秒")
            
    def stop_recording(self):
        """停止记录"""
        self.recording = False
        elapsed = time.time() - self.start_time if hasattr(self, 'start_time') else 0
        print(f"[INFO] 记录结束，时长: {elapsed:.2f} 秒")
        print(f"[INFO] 共记录 {len(self.recorded_data)} 条数据")
        
    def save_to_json(self, filename=None):
        """保存数据为JSON格式"""
        if not filename:
            filename = f'recording_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.recorded_data, f, indent=2, ensure_ascii=False)
            
        print(f"[INFO] 数据已保存到: {filepath}")
        return filepath
    
    def save_to_csv(self, filename=None):
        """保存数据为CSV格式"""
        if not filename:
            filename = f'recording_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            
        filepath = os.path.join(self.output_dir, filename)
        
        if not self.recorded_data:
            print("[WARNING] 没有数据可保存")
            return
            
        # 提取所有可能的字段
        fieldnames = set()
        for record in self.recorded_data:
            fieldnames.update(record.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in self.recorded_data:
                # 将嵌套字典转换为字符串
                flat_record = {}
                for key, value in record.items():
                    if isinstance(value, dict):
                        flat_record[key] = json.dumps(value)
                    else:
                        flat_record[key] = value
                writer.writerow(flat_record)
                
        print(f"[INFO] 数据已保存到: {filepath}")
        return filepath
    
    def analyze_data(self):
        """分析记录的数据"""
        if not self.recorded_data:
            print("[WARNING] 没有数据可分析")
            return
            
        print("\n" + "="*50)
        print("数据分析报告")
        print("="*50)
        
        # 统计各类数据
        data_types = {}
        for record in self.recorded_data:
            data_type = record.get('type', 'unknown')
            data_types[data_type] = data_types.get(data_type, 0) + 1
            
        print(f"\n数据类型统计:")
        for data_type, count in data_types.items():
            print(f"  - {data_type}: {count} 条")
            
        # 时间范围
        timestamps = [r['timestamp'] for r in self.recorded_data if 'timestamp' in r]
        if timestamps:
            print(f"\n时间范围:")
            print(f"  - 开始: {min(timestamps):.3f}")
            print(f"  - 结束: {max(timestamps):.3f}")
            print(f"  - 持续时间: {max(timestamps) - min(timestamps):.3f} 秒")
            
        print("="*50 + "\n")
    
    def cleanup(self):
        """清理资源"""
        self.stop_recording()
        
        # 销毁传感器
        for sensor in self.sensors:
            if sensor.is_alive:
                sensor.stop()
                sensor.destroy()
        self.sensors.clear()
        
        print("[INFO] 资源已清理")


class VehicleDataCollector:
    """车辆数据收集器"""
    
    def __init__(self, world, vehicle):
        """初始化"""
        self.world = world
        self.vehicle = vehicle
        self.trajectory = []
        self.speeds = []
        self.control_inputs = []
        
    def record_frame(self):
        """记录一帧数据"""
        transform = self.vehicle.get_transform()
        velocity = self.vehicle.get_velocity()
        control = self.vehicle.get_control()
        
        # 记录轨迹点
        self.trajectory.append({
            'x': transform.location.x,
            'y': transform.location.y,
            'z': transform.location.z,
            'yaw': transform.rotation.yaw,
            'timestamp': time.time()
        })
        
        # 记录速度
        speed = 3.6 * (velocity.x**2 + velocity.y**2 + velocity.z**2)**0.5  # km/h
        self.speeds.append(speed)
        
        # 记录控制输入
        self.control_inputs.append({
            'throttle': control.throttle,
            'steer': control.steer,
            'brake': control.brake,
            'reverse': control.reverse,
            'hand_brake': control.hand_brake,
            'manual_gear_shift': control.manual_gear_shift,
            'gear': control.gear
        })
    
    def get_summary(self):
        """获取数据摘要"""
        if not self.trajectory:
            return "没有数据"
            
        total_distance = 0
        for i in range(1, len(self.trajectory)):
            dx = self.trajectory[i]['x'] - self.trajectory[i-1]['x']
            dy = self.trajectory[i]['y'] - self.trajectory[i-1]['y']
            total_distance += (dx**2 + dy**2)**0.5
            
        avg_speed = sum(self.speeds) / len(self.speeds) if self.speeds else 0
        max_speed = max(self.speeds) if self.speeds else 0
        
        return {
            'total_points': len(self.trajectory),
            'total_distance': total_distance,
            'average_speed': avg_speed,
            'max_speed': max_speed,
            'duration': self.trajectory[-1]['timestamp'] - self.trajectory[0]['timestamp'] if len(self.trajectory) > 1 else 0
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='数据记录与分析模块')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--output', default='./recordings', help='输出目录')
    parser.add_argument('--duration', type=int, default=30, help='记录时长(秒)')
    
    args = parser.parse_args()
    
    recorder = DataRecorder(args.host, args.port, args.output)
    
    try:
        # 获取世界中的车辆
        vehicles = recorder.world.get_actors().filter('vehicle.*')
        if vehicles:
            vehicle = vehicles[0]
            print(f"[INFO] 找到车辆: {vehicle.type_id}")
            
            # 附加传感器
            recorder.attach_camera(vehicle, 'rgb')
            recorder.attach_gnss(vehicle)
            recorder.attach_imu(vehicle)
            
            # 开始记录
            recorder.start_recording(args.duration)
            
            print(f"[INFO] 记录中... 按 Ctrl+C 停止")
            time.sleep(args.duration)
            
            # 停止并保存
            recorder.stop_recording()
            recorder.save_to_json()
            recorder.save_to_csv()
            recorder.analyze_data()
        else:
            print("[WARNING] 未找到车辆，请先生成车辆")
            
    except KeyboardInterrupt:
        print("\n[INFO] 程序被中断")
    finally:
        recorder.cleanup()


if __name__ == '__main__':
    main()
