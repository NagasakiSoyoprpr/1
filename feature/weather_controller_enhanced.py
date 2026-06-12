#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气控制增强模块
基于已有dynamic_weather.py进行功能扩展，添加：
- 天气预设快速切换
- 天气时间序列记录
- 天气与车辆传感器联动
- 天气场景自动化测试
复现说明：
1. 启动CARLA模拟器（默认地址localhost:2000）
2. 运行命令：python weather_controller_enhanced.py --preset clear_noon
3. 可选参数：--preset 选择天气预设（clear_noon/cloudy_noon/wet_noon/hard_rain_noon/foggy_noon/clear_sunset/cloudy_night）
4. 查看效果：在模拟器中观察天气变化
"""

import carla
import random
import time
import json
import argparse
from datetime import datetime


class WeatherPreset:
    """天气预设管理"""
    PRESETS = {
        'clear_noon': {
            'name': '晴朗中午',
            'cloudiness': 30.0,
            'precipitation': 0.0,
            'precipitation_deposits': 0.0,
            'wind_intensity': 10.0,
            'sun_azimuth_angle': 0.0,
            'sun_altitude_angle': 70.0,
            'fog_density': 0.0,
            'wetness': 0.0
        },
        'cloudy_noon': {
            'name': '多云中午',
            'cloudiness': 80.0,
            'precipitation': 0.0,
            'precipitation_deposits': 0.0,
            'wind_intensity': 15.0,
            'sun_azimuth_angle': 0.0,
            'sun_altitude_angle': 60.0,
            'fog_density': 5.0,
            'wetness': 10.0
        },
        'wet_noon': {
            'name': '潮湿中午',
            'cloudiness': 60.0,
            'precipitation': 30.0,
            'precipitation_deposits': 50.0,
            'wind_intensity': 30.0,
            'sun_azimuth_angle': 0.0,
            'sun_altitude_angle': 55.0,
            'fog_density': 15.0,
            'wetness': 80.0
        },
        'hard_rain_noon': {
            'name': '暴雨中午',
            'cloudiness': 100.0,
            'precipitation': 100.0,
            'precipitation_deposits': 100.0,
            'wind_intensity': 100.0,
            'sun_azimuth_angle': 0.0,
            'sun_altitude_angle': 45.0,
            'fog_density': 30.0,
            'wetness': 100.0
        },
        'foggy_noon': {
            'name': '大雾中午',
            'cloudiness': 70.0,
            'precipitation': 0.0,
            'precipitation_deposits': 0.0,
            'wind_intensity': 5.0,
            'sun_azimuth_angle': 0.0,
            'sun_altitude_angle': 40.0,
            'fog_density': 80.0,
            'fog_distance': 20.0,
            'wetness': 30.0
        },
        'clear_sunset': {
            'name': '晴朗日落',
            'cloudiness': 20.0,
            'precipitation': 0.0,
            'precipitation_deposits': 0.0,
            'wind_intensity': 5.0,
            'sun_azimuth_angle': 180.0,
            'sun_altitude_angle': 10.0,
            'fog_density': 0.0,
            'wetness': 0.0
        },
        'cloudy_night': {
            'name': '多云夜晚',
            'cloudiness': 85.0,
            'precipitation': 0.0,
            'precipitation_deposits': 0.0,
            'wind_intensity': 10.0,
            'sun_azimuth_angle': 0.0,
            'sun_altitude_angle': -90.0,
            'fog_density': 10.0,
            'wetness': 20.0
        }
    }

    @classmethod
    def get_preset(cls, name):
        return cls.PRESETS.get(name, cls.PRESETS['clear_noon'])

    @classmethod
    def list_presets(cls):
        return list(cls.PRESETS.keys())


class WeatherRecorder:
    """天气记录器 - 记录天气变化历史"""
    def __init__(self, output_file=None):
        self.records = []
        self.output_file = output_file or f"weather_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    def record(self, weather, timestamp=None):
        record = {
            'timestamp': timestamp or time.time(),
            'cloudiness': weather.cloudiness,
            'precipitation': weather.precipitation,
            'wind_intensity': weather.wind_intensity,
            'fog_density': weather.fog_density,
            'wetness': weather.wetness,
            'sun_altitude_angle': weather.sun_altitude_angle
        }
        self.records.append(record)

    def save(self):
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, indent=2, ensure_ascii=False)
        print(f"[记录] 天气日志已保存: {self.output_file}")

    def get_summary(self):
        if not self.records:
            return "无记录"
        return {
            'total_records': len(self.records),
            'duration': self.records[-1]['timestamp'] - self.records[0]['timestamp'] if len(self.records) > 1 else 0,
            'weather_changes': sum(1 for i in range(1, len(self.records)) if self.records[i] != self.records[i-1])
        }


class WeatherControllerEnhanced:
    """增强版天气控制器"""

    def __init__(self, host='localhost', port=2000):
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.weather = self.world.get_weather()
        self.recorder = WeatherRecorder()
        print("[初始化] 天气控制增强模块已启动")

    def apply_preset(self, preset_name, record=True):
        """应用天气预设"""
        preset = WeatherPreset.get_preset(preset_name)
        print(f"[天气] 应用预设: {preset['name']}")

        weather = carla.WeatherParameters()
        for key, value in preset.items():
            if key != 'name' and hasattr(weather, key):
                setattr(weather, key, value)

        self.world.set_weather(weather)
        self.weather = weather

        if record:
            self.recorder.record(weather)

        return weather

    def smooth_transition(self, target_preset_name, duration=5.0, steps=50):
        """平滑过渡到目标天气"""
        target = WeatherPreset.get_preset(target_preset_name)
        print(f"[过渡] 平滑过渡到: {target['name']}，耗时: {duration}秒")

        start_values = {
            'cloudiness': self.weather.cloudiness,
            'precipitation': self.weather.precipitation,
            'precipitation_deposits': self.weather.precipitation_deposits,
            'wind_intensity': self.weather.wind_intensity,
            'fog_density': self.weather.fog_density,
            'wetness': self.weather.wetness,
            'sun_altitude_angle': self.weather.sun_altitude_angle
        }

        target_values = {k: v for k, v in target.items() if k != 'name'}

        for i in range(steps + 1):
            t = i / steps
            weather = carla.WeatherParameters()

            for key in target_values:
                if key in ['sun_azimuth_angle', 'sun_altitude_angle']:
                    # 角度需要特殊处理
                    start_val = start_values.get(key, 0)
                    target_val = target_values[key]
                    current_val = start_val + (target_val - start_val) * t
                else:
                    start_val = start_values.get(key, 0)
                    target_val = target_values[key]
                    current_val = start_val + (target_val - start_val) * t

                setattr(weather, key, current_val)

            self.world.set_weather(weather)
            time.sleep(duration / steps)

        self.weather = weather
        self.recorder.record(weather)
        print(f"[过渡] 完成")

    def auto_weather_cycle(self, presets=None, interval=30.0, smooth=True):
        """自动天气循环"""
        if presets is None:
            presets = ['clear_noon', 'cloudy_noon', 'wet_noon', 'clear_sunset', 'cloudy_night']

        print(f"[循环] 启动自动天气循环，间隔: {interval}秒")
        print(f"[循环] 预设序列: {presets}")
        print("[循环] 按 Ctrl+C 停止")

        try:
            while True:
                for preset_name in presets:
                    if smooth:
                        self.smooth_transition(preset_name, duration=5.0)
                    else:
                        self.apply_preset(preset_name)
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[循环] 已停止")
            self.recorder.save()

    def test_sensor_in_weather(self, vehicle, weather_preset, duration=10.0):
        """测试特定天气下的传感器性能"""
        print(f"[测试] 在 {weather_preset} 天气下测试传感器")
        self.apply_preset(weather_preset)

        # 获取车辆传感器
        sensors = []
        for actor in self.world.get_actors():
            if actor.parent == vehicle and 'sensor' in actor.type_id:
                sensors.append(actor)

        print(f"[测试] 发现 {len(sensors)} 个传感器")
        for sensor in sensors:
            print(f"  - {sensor.type_id}")

        time.sleep(duration)
        print("[测试] 完成")

    def generate_weather_report(self):
        """生成天气测试报告"""
        summary = self.recorder.get_summary()
        report = {
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'available_presets': WeatherPreset.list_presets(),
            'current_weather': {
                'cloudiness': self.weather.cloudiness,
                'precipitation': self.weather.precipitation,
                'wind_intensity': self.weather.wind_intensity,
                'fog_density': self.weather.fog_density,
                'wetness': self.weather.wetness,
                'sun_altitude_angle': self.weather.sun_altitude_angle
            }
        }
        return report


def main():
    parser = argparse.ArgumentParser(description='天气控制增强模块')
    parser.add_argument('--host', default='localhost', help='主机地址')
    parser.add_argument('--port', type=int, default=2000, help='端口')
    parser.add_argument('--preset', default='clear_noon', help='天气预设')
    parser.add_argument('--mode', default='preset',
                       choices=['preset', 'cycle', 'smooth', 'test'],
                       help='运行模式')
    parser.add_argument('--interval', type=float, default=30.0, help='循环间隔')

    args = parser.parse_args()

    controller = WeatherControllerEnhanced(args.host, args.port)

    if args.mode == 'preset':
        controller.apply_preset(args.preset)
        print("\n当前天气报告:")
        print(json.dumps(controller.generate_weather_report(), indent=2, ensure_ascii=False))

    elif args.mode == 'cycle':
        controller.auto_weather_cycle(interval=args.interval)

    elif args.mode == 'smooth':
        presets = ['clear_noon', 'cloudy_noon', 'wet_noon', 'hard_rain_noon', 'foggy_noon']
        for preset in presets:
            controller.smooth_transition(preset, duration=3.0)
            time.sleep(2.0)

    elif args.mode == 'test':
        vehicles = controller.world.get_actors().filter('vehicle.*')
        if vehicles:
            controller.test_sensor_in_weather(vehicles[0], args.preset)
        else:
            print("[错误] 未找到车辆")


if __name__ == '__main__':
    main()
