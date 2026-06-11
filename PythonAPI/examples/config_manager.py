#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模拟环境配置管理器
管理模拟器环境配置，包括地图、天气、交通等参数的保存和加载
"""

import carla
import json
import os
import time
import argparse
from datetime import datetime


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, host='localhost', port=2000, config_dir='./configs'):
        """初始化配置管理器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.config_dir = config_dir
        
        # 创建配置目录
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        print(f"[INFO] 配置管理器已初始化，配置目录: {config_dir}")
        
    def get_current_config(self):
        """获取当前环境配置"""
        config = {
            'timestamp': datetime.now().isoformat(),
            'map': self.world.get_map().name,
            'weather': self._get_weather_config(),
            'settings': self._get_world_settings(),
            'actors': self._get_actor_config()
        }
        return config
        
    def _get_weather_config(self):
        """获取天气配置"""
        weather = self.world.get_weather()
        return {
            'cloudiness': weather.cloudiness,
            'precipitation': weather.precipitation,
            'precipitation_deposits': weather.precipitation_deposits,
            'wind_intensity': weather.wind_intensity,
            'sun_azimuth_angle': weather.sun_azimuth_angle,
            'sun_altitude_angle': weather.sun_altitude_angle,
            'fog_density': weather.fog_density,
            'fog_distance': weather.fog_distance,
            'fog_falloff': weather.fog_falloff,
            'wetness': weather.wetness,
            'scattering_intensity': weather.scattering_intensity,
            'mie_scattering_scale': weather.mie_scattering_scale,
            'rayleigh_scattering_scale': weather.rayleigh_scattering_scale
        }
        
    def _get_world_settings(self):
        """获取世界设置"""
        settings = self.world.get_settings()
        return {
            'synchronous_mode': settings.synchronous_mode,
            'fixed_delta_seconds': settings.fixed_delta_seconds,
            'substepping': settings.substepping,
            'max_substep_delta_time': settings.max_substep_delta_time,
            'max_substeps': settings.max_substeps
        }
        
    def _get_actor_config(self):
        """获取 actor 配置"""
        actors = []
        for actor in self.world.get_actors():
            if actor.type_id.startswith('vehicle') or actor.type_id.startswith('walker'):
                actors.append({
                    'type_id': actor.type_id,
                    'id': actor.id,
                    'location': {
                        'x': actor.get_location().x,
                        'y': actor.get_location().y,
                        'z': actor.get_location().z
                    },
                    'rotation': {
                        'pitch': actor.get_transform().rotation.pitch,
                        'yaw': actor.get_transform().rotation.yaw,
                        'roll': actor.get_transform().rotation.roll
                    }
                })
        return actors
        
    def save_config(self, config_name=None):
        """保存当前配置"""
        if not config_name:
            config_name = f"config_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
        config = self.get_current_config()
        filepath = os.path.join(self.config_dir, f"{config_name}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        print(f"[INFO] 配置已保存: {filepath}")
        return filepath
        
    def load_config(self, config_name):
        """加载配置"""
        filepath = os.path.join(self.config_dir, f"{config_name}.json")
        
        if not os.path.exists(filepath):
            print(f"[ERROR] 配置文件不存在: {filepath}")
            return None
            
        with open(filepath, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        print(f"[INFO] 配置已加载: {filepath}")
        return config
        
    def apply_config(self, config):
        """应用配置"""
        print("[INFO] 开始应用配置...")
        
        # 应用天气
        if 'weather' in config:
            self._apply_weather(config['weather'])
            
        # 应用世界设置
        if 'settings' in config:
            self._apply_settings(config['settings'])
            
        print("[INFO] 配置应用完成")
        
    def _apply_weather(self, weather_config):
        """应用天气配置"""
        weather = carla.WeatherParameters()
        weather.cloudiness = weather_config.get('cloudiness', 30.0)
        weather.precipitation = weather_config.get('precipitation', 0.0)
        weather.precipitation_deposits = weather_config.get('precipitation_deposits', 0.0)
        weather.wind_intensity = weather_config.get('wind_intensity', 0.0)
        weather.sun_azimuth_angle = weather_config.get('sun_azimuth_angle', 0.0)
        weather.sun_altitude_angle = weather_config.get('sun_altitude_angle', 45.0)
        weather.fog_density = weather_config.get('fog_density', 0.0)
        weather.fog_distance = weather_config.get('fog_distance', 0.0)
        weather.fog_falloff = weather_config.get('fog_falloff', 0.0)
        weather.wetness = weather_config.get('wetness', 0.0)
        weather.scattering_intensity = weather_config.get('scattering_intensity', 1.0)
        weather.mie_scattering_scale = weather_config.get('mie_scattering_scale', 0.03)
        weather.rayleigh_scattering_scale = weather_config.get('rayleigh_scattering_scale', 0.0331)
        
        self.world.set_weather(weather)
        print("[INFO] 天气配置已应用")
        
    def _apply_settings(self, settings_config):
        """应用世界设置"""
        settings = self.world.get_settings()
        settings.synchronous_mode = settings_config.get('synchronous_mode', False)
        settings.fixed_delta_seconds = settings_config.get('fixed_delta_seconds', None)
        settings.substepping = settings_config.get('substepping', True)
        settings.max_substep_delta_time = settings_config.get('max_substep_delta_time', 0.01)
        settings.max_substeps = settings_config.get('max_substeps', 10)
        
        self.world.apply_settings(settings)
        print("[INFO] 世界设置已应用")
        
    def list_configs(self):
        """列出所有配置"""
        configs = []
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                configs.append(filename[:-5])  # 去掉 .json 后缀
        return configs
        
    def create_preset(self, preset_name):
        """创建预设配置"""
        presets = {
            'sunny_day': {
                'cloudiness': 10.0,
                'precipitation': 0.0,
                'sun_altitude_angle': 70.0,
                'fog_density': 0.0
            },
            'rainy_day': {
                'cloudiness': 80.0,
                'precipitation': 60.0,
                'precipitation_deposits': 60.0,
                'wind_intensity': 30.0,
                'sun_altitude_angle': 30.0,
                'wetness': 60.0
            },
            'foggy_morning': {
                'cloudiness': 50.0,
                'fog_density': 80.0,
                'fog_distance': 20.0,
                'sun_altitude_angle': 10.0
            },
            'night_clear': {
                'cloudiness': 0.0,
                'sun_altitude_angle': -90.0,
                'precipitation': 0.0
            },
            'storm': {
                'cloudiness': 100.0,
                'precipitation': 100.0,
                'wind_intensity': 100.0,
                'sun_altitude_angle': 20.0
            }
        }
        
        if preset_name in presets:
            config = {
                'timestamp': datetime.now().isoformat(),
                'map': self.world.get_map().name,
                'weather': presets[preset_name],
                'settings': self._get_world_settings(),
                'actors': []
            }
            
            filepath = os.path.join(self.config_dir, f"preset_{preset_name}.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            print(f"[INFO] 预设配置已创建: {preset_name}")
            return filepath
        else:
            print(f"[ERROR] 未知预设: {preset_name}")
            print(f"[INFO] 可用预设: {', '.join(presets.keys())}")
            return None
            
    def compare_configs(self, config1_name, config2_name):
        """比较两个配置"""
        config1 = self.load_config(config1_name)
        config2 = self.load_config(config2_name)
        
        if not config1 or not config2:
            return
            
        print("\n" + "="*50)
        print("配置对比")
        print("="*50)
        
        # 比较地图
        if config1.get('map') != config2.get('map'):
            print(f"地图不同: {config1.get('map')} vs {config2.get('map')}")
        else:
            print(f"地图相同: {config1.get('map')}")
            
        # 比较天气
        weather1 = config1.get('weather', {})
        weather2 = config2.get('weather', {})
        
        print("\n天气差异:")
        all_keys = set(weather1.keys()) | set(weather2.keys())
        for key in all_keys:
            val1 = weather1.get(key, 'N/A')
            val2 = weather2.get(key, 'N/A')
            if val1 != val2:
                print(f"  {key}: {val1} -> {val2}")
                
        print("="*50 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='模拟环境配置管理器')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--action', default='save',
                       choices=['save', 'load', 'list', 'preset', 'compare'],
                       help='操作类型')
    parser.add_argument('--name', help='配置名称')
    parser.add_argument('--config1', help='对比配置1')
    parser.add_argument('--config2', help='对比配置2')
    
    args = parser.parse_args()
    
    manager = ConfigManager(args.host, args.port)
    
    if args.action == 'save':
        manager.save_config(args.name)
        
    elif args.action == 'load':
        if not args.name:
            print("[ERROR] 请指定配置名称 (--name)")
            return
        config = manager.load_config(args.name)
        if config:
            manager.apply_config(config)
            
    elif args.action == 'list':
        configs = manager.list_configs()
        print("[INFO] 可用配置:")
        for config in configs:
            print(f"  - {config}")
            
    elif args.action == 'preset':
        if not args.name:
            print("[ERROR] 请指定预设名称 (--name)")
            print("[INFO] 可用预设: sunny_day, rainy_day, foggy_morning, night_clear, storm")
            return
        manager.create_preset(args.name)
        
    elif args.action == 'compare':
        if not args.config1 or not args.config2:
            print("[ERROR] 请指定两个配置 (--config1, --config2)")
            return
        manager.compare_configs(args.config1, args.config2)


if __name__ == '__main__':
    main()
