#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气控制系统
用于动态控制模拟器中的天气参数
"""

import carla
import random
import time
import argparse


class WeatherController:
    """天气控制器类，用于动态调整模拟器天气参数"""
    
    def __init__(self, host='localhost', port=2000):
        """初始化天气控制器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.weather = self.world.get_weather()
        print(f"[INFO] 已连接到模拟器: {host}:{port}")
        
    def set_sunny(self):
        """设置晴天"""
        self.weather.cloudiness = 10.0
        self.weather.precipitation = 0.0
        self.weather.precipitation_deposits = 0.0
        self.weather.wind_intensity = 10.0
        self.weather.fog_density = 0.0
        self.weather.wetness = 0.0
        self.world.set_weather(self.weather)
        print("[天气] 已设置为：晴天 ☀️")
        
    def set_rainy(self, intensity=50.0):
        """设置雨天"""
        self.weather.cloudiness = 80.0
        self.weather.precipitation = intensity
        self.weather.precipitation_deposits = intensity * 0.8
        self.weather.wind_intensity = 30.0
        self.weather.fog_density = 10.0
        self.weather.wetness = intensity
        self.world.set_weather(self.weather)
        print(f"[天气] 已设置为：雨天 🌧️ (强度: {intensity}%)")
        
    def set_foggy(self, density=50.0):
        """设置雾天"""
        self.weather.cloudiness = 60.0
        self.weather.precipitation = 0.0
        self.weather.precipitation_deposits = 0.0
        self.weather.wind_intensity = 5.0
        self.weather.fog_density = density
        self.weather.fog_distance = 50.0
        self.weather.wetness = 20.0
        self.world.set_weather(self.weather)
        print(f"[天气] 已设置为：雾天 🌫️ (密度: {density}%)")
        
    def set_snowy(self, intensity=60.0):
        """设置雪天"""
        self.weather.cloudiness = 90.0
        self.weather.precipitation = intensity
        self.weather.precipitation_deposits = intensity * 0.9
        self.weather.wind_intensity = 40.0
        self.weather.fog_density = 20.0
        self.weather.wetness = 0.0
        self.weather.sun_altitude_angle = 20.0
        self.world.set_weather(self.weather)
        print(f"[天气] 已设置为：雪天 ❄️ (强度: {intensity}%)")
        
    def set_storm(self):
        """设置暴风雨"""
        self.weather.cloudiness = 100.0
        self.weather.precipitation = 100.0
        self.weather.precipitation_deposits = 100.0
        self.weather.wind_intensity = 100.0
        self.weather.fog_density = 30.0
        self.weather.wetness = 100.0
        self.world.set_weather(self.weather)
        print("[天气] 已设置为：暴风雨 ⛈️")
        
    def set_custom(self, cloudiness=30.0, precipitation=0.0, 
                   wind_intensity=10.0, fog_density=0.0, sun_altitude=45.0):
        """设置自定义天气"""
        self.weather.cloudiness = cloudiness
        self.weather.precipitation = precipitation
        self.weather.precipitation_deposits = precipitation * 0.5
        self.weather.wind_intensity = wind_intensity
        self.weather.fog_density = fog_density
        self.weather.sun_altitude_angle = sun_altitude
        self.world.set_weather(self.weather)
        print("[天气] 已设置为：自定义天气 ⚙️")
        
    def cycle_weather(self, interval=10):
        """循环切换天气效果"""
        weather_modes = [
            self.set_sunny,
            self.set_rainy,
            self.set_foggy,
            self.set_snowy,
            self.set_storm
        ]
        
        print(f"[INFO] 开始天气循环演示，每 {interval} 秒切换一次")
        print("[INFO] 按 Ctrl+C 停止")
        
        try:
            while True:
                for mode in weather_modes:
                    mode()
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[INFO] 天气循环已停止")
            
    def get_current_weather(self):
        """获取当前天气状态"""
        w = self.weather
        return {
            'cloudiness': w.cloudiness,
            'precipitation': w.precipitation,
            'wind_intensity': w.wind_intensity,
            'fog_density': w.fog_density,
            'wetness': w.wetness,
            'sun_altitude': w.sun_altitude_angle
        }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='天气控制系统')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--mode', default='sunny', 
                       choices=['sunny', 'rainy', 'foggy', 'snowy', 'storm', 'cycle'],
                       help='天气模式')
    parser.add_argument('--interval', type=int, default=10, help='循环间隔(秒)')
    
    args = parser.parse_args()
    
    try:
        controller = WeatherController(args.host, args.port)
        
        if args.mode == 'sunny':
            controller.set_sunny()
        elif args.mode == 'rainy':
            controller.set_rainy()
        elif args.mode == 'foggy':
            controller.set_foggy()
        elif args.mode == 'snowy':
            controller.set_snowy()
        elif args.mode == 'storm':
            controller.set_storm()
        elif args.mode == 'cycle':
            controller.cycle_weather(args.interval)
            
    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == '__main__':
    main()
