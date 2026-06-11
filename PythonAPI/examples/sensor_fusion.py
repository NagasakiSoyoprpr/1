#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多传感器融合模块
融合摄像头、激光雷达、毫米波雷达等多传感器数据

复现说明：
  1. 启动CARLA模拟器（任意地图均可，推荐Town03）
  2. 确保场景中已有车辆（可通过模拟器UI手动生成，或使用其他脚本生成）
  3. 运行脚本：
     python sensor_fusion.py                          # 使用默认参数（连接localhost:2000，10Hz融合频率）
     python sensor_fusion.py --host localhost --port 2000 --frequency 5  # 自定义参数
  4. 参数说明：
     --host     : 模拟器主机地址（默认：localhost）
     --port     : 模拟器端口（默认：2000）
     --frequency : 融合频率，单位Hz（默认：10）
  5. 注意事项：
     - 场景中必须至少有一辆车辆，脚本会自动为第一辆车挂载传感器
     - 如果某些传感器蓝图不存在，会跳过该传感器并继续运行
     - 本脚本不依赖numpy，使用纯Python实现所有计算
  6. 按 Ctrl+C 停止运行
"""

import carla
import time
import math
import struct
import threading
from collections import deque
import argparse


class SensorData:
    """传感器数据类"""
    def __init__(self, sensor_type, timestamp, data, transform):
        self.sensor_type = sensor_type
        self.timestamp = timestamp
        self.data = data
        self.transform = transform


class SensorFusion:
    """多传感器融合类"""

    def __init__(self, host='localhost', port=2000):
        """初始化传感器融合模块"""
        try:
            self.client = carla.Client(host, port)
            self.client.set_timeout(10.0)
            self.world = self.client.get_world()
        except Exception as e:
            print(f"[ERROR] 连接CARLA模拟器失败: {e}")
            raise

        self.sensors = {}
        self.data_buffer = {}
        self.fusion_results = deque(maxlen=100)
        self.running = False
        self.fusion_thread = None

        print("[INFO] 多传感器融合模块已初始化")

    def _safe_spawn_sensor(self, bp_name, transform, attach_to, callback):
        """安全地生成传感器，失败时返回None"""
        try:
            blueprint_library = self.world.get_blueprint_library()
            bp = blueprint_library.find(bp_name)
            if bp is None:
                print(f"[WARNING] 未找到传感器蓝图: {bp_name}，跳过")
                return None
            sensor = self.world.spawn_actor(bp, transform, attach_to=attach_to)
            sensor.listen(callback)
            return sensor
        except Exception as e:
            print(f"[WARNING] 生成传感器 {bp_name} 失败: {e}")
            return None

    def setup_sensor_suite(self, vehicle):
        """为车辆配置传感器套件"""
        blueprint_library = self.world.get_blueprint_library()

        # 1. RGB摄像头
        try:
            camera_bp = blueprint_library.find('sensor.camera.rgb')
            if camera_bp:
                camera_bp.set_attribute('image_size_x', '800')
                camera_bp.set_attribute('image_size_y', '600')
                camera_bp.set_attribute('fov', '110')
                camera_transform = carla.Transform(carla.Location(x=1.6, z=1.7))
                camera = self.world.spawn_actor(
                    camera_bp, camera_transform, attach_to=vehicle
                )
                camera.listen(lambda data: self._process_camera_data(data))
                self.sensors['camera'] = camera
                self.data_buffer['camera'] = deque(maxlen=10)
                print(f"  - RGB摄像头: {camera.id}")
            else:
                print("  [WARNING] 未找到 sensor.camera.rgb 蓝图，跳过摄像头")
        except Exception as e:
            print(f"  [WARNING] 配置摄像头失败: {e}")

        # 2. 激光雷达
        try:
            lidar_bp = blueprint_library.find('sensor.lidar.ray_cast')
            if lidar_bp:
                lidar_bp.set_attribute('range', '100')
                lidar_bp.set_attribute('rotation_frequency', '10')
                lidar_bp.set_attribute('channels', '64')
                lidar_bp.set_attribute('points_per_second', '100000')
                lidar_transform = carla.Transform(carla.Location(x=0, z=2.4))
                lidar = self.world.spawn_actor(
                    lidar_bp, lidar_transform, attach_to=vehicle
                )
                lidar.listen(lambda data: self._process_lidar_data(data))
                self.sensors['lidar'] = lidar
                self.data_buffer['lidar'] = deque(maxlen=10)
                print(f"  - 激光雷达: {lidar.id}")
            else:
                print("  [WARNING] 未找到 sensor.lidar.ray_cast 蓝图，跳过激光雷达")
        except Exception as e:
            print(f"  [WARNING] 配置激光雷达失败: {e}")

        # 3. 毫米波雷达
        try:
            radar_bp = blueprint_library.find('sensor.other.radar')
            if radar_bp:
                radar_bp.set_attribute('horizontal_fov', '30')
                radar_bp.set_attribute('vertical_fov', '30')
                radar_bp.set_attribute('range', '100')
                radar_transform = carla.Transform(carla.Location(x=2.0, z=1.0))
                radar = self.world.spawn_actor(
                    radar_bp, radar_transform, attach_to=vehicle
                )
                radar.listen(lambda data: self._process_radar_data(data))
                self.sensors['radar'] = radar
                self.data_buffer['radar'] = deque(maxlen=10)
                print(f"  - 毫米波雷达: {radar.id}")
            else:
                print("  [WARNING] 未找到 sensor.other.radar 蓝图，跳过毫米波雷达")
        except Exception as e:
            print(f"  [WARNING] 配置毫米波雷达失败: {e}")

        # 4. GNSS
        try:
            gnss_bp = blueprint_library.find('sensor.other.gnss')
            if gnss_bp:
                gnss_transform = carla.Transform(carla.Location(x=0, z=2.0))
                gnss = self.world.spawn_actor(
                    gnss_bp, gnss_transform, attach_to=vehicle
                )
                gnss.listen(lambda data: self._process_gnss_data(data))
                self.sensors['gnss'] = gnss
                self.data_buffer['gnss'] = deque(maxlen=10)
                print(f"  - GNSS: {gnss.id}")
            else:
                print("  [WARNING] 未找到 sensor.other.gnss 蓝图，跳过GNSS")
        except Exception as e:
            print(f"  [WARNING] 配置GNSS失败: {e}")

        # 5. IMU
        try:
            imu_bp = blueprint_library.find('sensor.other.imu')
            if imu_bp:
                imu_transform = carla.Transform(carla.Location(x=0, z=2.0))
                imu = self.world.spawn_actor(
                    imu_bp, imu_transform, attach_to=vehicle
                )
                imu.listen(lambda data: self._process_imu_data(data))
                self.sensors['imu'] = imu
                self.data_buffer['imu'] = deque(maxlen=10)
                print(f"  - IMU: {imu.id}")
            else:
                print("  [WARNING] 未找到 sensor.other.imu 蓝图，跳过IMU")
        except Exception as e:
            print(f"  [WARNING] 配置IMU失败: {e}")

        print(f"[INFO] 传感器套件配置完成，共 {len(self.sensors)} 个传感器")

    def _process_camera_data(self, data):
        """处理摄像头数据"""
        try:
            sensor_data = SensorData(
                'camera',
                data.timestamp,
                {
                    'frame': data.frame,
                    'width': data.width,
                    'height': data.height,
                    'fov': data.fov
                },
                data.transform
            )
            self.data_buffer['camera'].append(sensor_data)
        except Exception:
            pass

    def _process_lidar_data(self, data):
        """处理激光雷达数据（纯Python实现，不依赖numpy）"""
        try:
            # 使用struct解析二进制数据，避免numpy依赖
            raw_bytes = bytes(data.raw_data)
            # 每个点4个float32值 (x, y, z, intensity)
            point_size = 4 * 4  # 16 bytes
            num_points = len(raw_bytes) // point_size

            points = []
            for i in range(num_points):
                offset = i * point_size
                x, y, z, intensity = struct.unpack_from('ffff', raw_bytes, offset)
                points.append((x, y, z, intensity))

            sensor_data = SensorData(
                'lidar',
                data.timestamp,
                {
                    'frame': data.frame,
                    'point_count': num_points,
                    'points': points
                },
                data.transform
            )
            self.data_buffer['lidar'].append(sensor_data)
        except Exception as e:
            print(f"[WARNING] 处理激光雷达数据失败: {e}")

    def _process_radar_data(self, data):
        """处理毫米波雷达数据"""
        try:
            detections = []
            for detection in data:
                detections.append({
                    'velocity': detection.velocity,
                    'azimuth': detection.azimuth,
                    'altitude': detection.altitude,
                    'depth': detection.depth
                })

            sensor_data = SensorData(
                'radar',
                data.timestamp,
                {
                    'frame': data.frame,
                    'detection_count': len(detections),
                    'detections': detections
                },
                data.transform
            )
            self.data_buffer['radar'].append(sensor_data)
        except Exception:
            pass

    def _process_gnss_data(self, data):
        """处理GNSS数据"""
        try:
            sensor_data = SensorData(
                'gnss',
                data.timestamp,
                {
                    'latitude': data.latitude,
                    'longitude': data.longitude,
                    'altitude': data.altitude
                },
                data.transform
            )
            self.data_buffer['gnss'].append(sensor_data)
        except Exception:
            pass

    def _process_imu_data(self, data):
        """处理IMU数据"""
        try:
            sensor_data = SensorData(
                'imu',
                data.timestamp,
                {
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
                },
                data.transform
            )
            self.data_buffer['imu'].append(sensor_data)
        except Exception:
            pass

    def fuse_data(self):
        """执行传感器融合"""
        # 获取最新的传感器数据
        latest_data = {}
        for sensor_type, buffer in self.data_buffer.items():
            if buffer:
                latest_data[sensor_type] = buffer[-1]

        if len(latest_data) < 2:
            return None

        # 时间同步检查
        timestamps = [d.timestamp for d in latest_data.values()]
        time_diff = max(timestamps) - min(timestamps)

        if time_diff > 0.1:
            print(f"[WARNING] 传感器时间不同步: {time_diff * 1000:.1f}ms")

        # 执行融合
        fusion_result = {
            'timestamp': time.time(),
            'sensor_count': len(latest_data),
            'time_sync_diff': time_diff,
            'objects': [],
            'ego_state': {}
        }

        # 融合雷达和激光雷达检测目标
        if 'radar' in latest_data and 'lidar' in latest_data:
            try:
                fused_objects = self._fuse_radar_lidar(
                    latest_data['radar'].data,
                    latest_data['lidar'].data
                )
                fusion_result['objects'] = fused_objects
            except Exception as e:
                print(f"[WARNING] 雷达-激光雷达融合失败: {e}")

        # 融合定位信息
        if 'gnss' in latest_data and 'imu' in latest_data:
            try:
                ego_state = self._fuse_localization(
                    latest_data['gnss'].data,
                    latest_data['imu'].data
                )
                fusion_result['ego_state'] = ego_state
            except Exception as e:
                print(f"[WARNING] 定位融合失败: {e}")

        self.fusion_results.append(fusion_result)
        return fusion_result

    def _fuse_radar_lidar(self, radar_data, lidar_data):
        """融合雷达和激光雷达数据（纯Python实现）"""
        fused_objects = []

        # 从激光雷达提取目标
        if lidar_data['point_count'] > 0:
            points = lidar_data['points']

            # 纯Python计算点云统计特征
            n = len(points)
            if n > 0:
                sum_x = sum(p[0] for p in points)
                sum_y = sum(p[1] for p in points)
                sum_z = sum(p[2] for p in points)
                mean_x = sum_x / n
                mean_y = sum_y / n
                mean_z = sum_z / n

                # 标准差
                if n > 1:
                    var_x = sum((p[0] - mean_x) ** 2 for p in points) / (n - 1)
                    var_y = sum((p[1] - mean_y) ** 2 for p in points) / (n - 1)
                    var_z = sum((p[2] - mean_z) ** 2 for p in points) / (n - 1)
                    std_x = var_x ** 0.5
                    std_y = var_y ** 0.5
                    std_z = var_z ** 0.5
                else:
                    std_x = std_y = std_z = 0.0

                fused_objects.append({
                    'source': 'lidar',
                    'point_count': lidar_data['point_count'],
                    'mean_position': [mean_x, mean_y, mean_z],
                    'std_position': [std_x, std_y, std_z]
                })

        # 添加雷达检测
        for detection in radar_data.get('detections', []):
            fused_objects.append({
                'source': 'radar',
                'depth': detection['depth'],
                'velocity': detection['velocity'],
                'azimuth': detection['azimuth']
            })

        return fused_objects

    def _fuse_localization(self, gnss_data, imu_data):
        """融合定位信息"""
        ego_state = {
            'position': {
                'latitude': gnss_data['latitude'],
                'longitude': gnss_data['longitude'],
                'altitude': gnss_data['altitude']
            },
            'acceleration': imu_data['accelerometer'],
            'angular_velocity': imu_data['gyroscope'],
            'heading': imu_data['compass']
        }

        return ego_state

    def start_fusion(self, frequency=10):
        """启动融合线程"""
        self.running = True
        interval = 1.0 / frequency

        def fusion_loop():
            while self.running:
                try:
                    result = self.fuse_data()
                    if result:
                        print(f"[融合] 检测到 {len(result['objects'])} 个目标")
                except Exception as e:
                    print(f"[WARNING] 融合循环异常: {e}")
                time.sleep(interval)

        self.fusion_thread = threading.Thread(target=fusion_loop, daemon=True)
        self.fusion_thread.start()
        print(f"[INFO] 融合线程已启动，频率: {frequency}Hz")

    def stop_fusion(self):
        """停止融合"""
        self.running = False
        if self.fusion_thread and self.fusion_thread.is_alive():
            self.fusion_thread.join(timeout=2.0)
        print("[INFO] 融合线程已停止")

    def get_fusion_report(self):
        """获取融合报告"""
        if not self.fusion_results:
            return "没有融合数据"

        latest = self.fusion_results[-1]

        report_lines = [
            "========== 传感器融合报告 ==========",
            f"时间戳: {latest['timestamp']:.3f}",
            f"传感器数量: {latest['sensor_count']}",
            f"时间同步差异: {latest['time_sync_diff'] * 1000:.1f}ms",
            "",
            f"检测目标: {len(latest['objects'])}"
        ]

        for i, obj in enumerate(latest['objects'][:5]):
            report_lines.append(f"  [{i + 1}] 来源: {obj.get('source', 'unknown')}")
            if 'point_count' in obj:
                report_lines.append(f"      点数: {obj['point_count']}")
            if 'depth' in obj:
                report_lines.append(f"      距离: {obj['depth']:.2f}m")

        if latest['ego_state']:
            report_lines.append("")
            report_lines.append("自车状态:")
            pos = latest['ego_state']['position']
            report_lines.append(f"  位置: ({pos['latitude']:.6f}, {pos['longitude']:.6f})")
            report_lines.append(f"  航向: {latest['ego_state']['heading']:.2f} deg")

        report_lines.append("=" * 40)
        return "\n".join(report_lines)

    def cleanup(self):
        """清理资源"""
        self.stop_fusion()

        for name, sensor in self.sensors.items():
            try:
                if sensor.is_alive:
                    sensor.stop()
                    sensor.destroy()
                    print(f"[INFO] 传感器 {name} 已销毁")
            except Exception as e:
                print(f"[WARNING] 销毁传感器 {name} 失败: {e}")
        self.sensors.clear()

        print("[INFO] 传感器资源已清理")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='多传感器融合模块')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--frequency', type=int, default=10, help='融合频率(Hz)')

    args = parser.parse_args()

    fusion = None
    try:
        fusion = SensorFusion(args.host, args.port)

        # 获取车辆
        vehicles = fusion.world.get_actors().filter('vehicle.*')
        if vehicles:
            vehicle = vehicles[0]
            print(f"[INFO] 找到车辆: {vehicle.type_id}")

            # 配置传感器
            fusion.setup_sensor_suite(vehicle)

            # 启动融合
            fusion.start_fusion(args.frequency)

            print("[INFO] 按 Ctrl+C 停止")
            while True:
                time.sleep(2)
                report = fusion.get_fusion_report()
                print(report)
        else:
            print("[WARNING] 未找到车辆，请先在场景中生成车辆")

    except KeyboardInterrupt:
        print("\n[INFO] 程序被中断")
    except Exception as e:
        print(f"[ERROR] 程序异常: {e}")
    finally:
        if fusion is not None:
            fusion.cleanup()


if __name__ == '__main__':
    main()
