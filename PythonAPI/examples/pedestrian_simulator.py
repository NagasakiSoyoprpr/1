#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行人行为模拟器
模拟行人的各种行为模式，包括行走、等待、穿越马路等
"""

import carla
import random
import time
import math
import argparse
from enum import Enum


class PedestrianState(Enum):
    """行人状态枚举"""
    WALKING = 0
    WAITING = 1
    CROSSING = 2
    IDLE = 3
    RUNNING = 4


class PedestrianAgent:
    """行人类"""
    
    def __init__(self, world, walker, controller):
        """初始化行人代理"""
        self.world = world
        self.walker = walker
        self.controller = controller
        self.state = PedestrianState.IDLE
        self.destination = None
        self.speed = 1.4  # 默认步行速度 m/s
        self.id = walker.id
        
    def set_destination(self, location):
        """设置目的地"""
        self.destination = location
        if self.controller:
            self.controller.go_to_location(location)
            self.controller.set_max_speed(self.speed)
        self.state = PedestrianState.WALKING
        
    def wait(self, duration):
        """等待一段时间"""
        self.state = PedestrianState.WAITING
        if self.controller:
            self.controller.stop()
        time.sleep(duration)
        
    def cross_road(self, start_point, end_point):
        """穿越马路"""
        self.state = PedestrianState.CROSSING
        self.speed = 1.2  # 过马路时稍快
        self.set_destination(end_point)
        
    def run(self, destination):
        """奔跑"""
        self.state = PedestrianState.RUNNING
        self.speed = 3.5  # 跑步速度
        self.set_destination(destination)
        
    def get_location(self):
        """获取当前位置"""
        return self.walker.get_location()
    
    def destroy(self):
        """销毁行人"""
        if self.controller:
            self.controller.stop()
            self.controller.destroy()
        if self.walker:
            self.walker.destroy()


class PedestrianSimulator:
    """行人模拟器"""
    
    def __init__(self, host='localhost', port=2000):
        """初始化行人模拟器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.pedestrians = []
        self.walker_blueprints = []
        self.running = False
        print("[INFO] 行人模拟器已初始化")
        
    def load_walker_blueprints(self):
        """加载行人蓝图"""
        blueprint_library = self.world.get_blueprint_library()
        self.walker_blueprints = blueprint_library.filter('walker.pedestrian.*')
        print(f"[INFO] 加载了 {len(self.walker_blueprints)} 种行人类型")
        return self.walker_blueprints
    
    def spawn_pedestrian(self, transform=None, behavior='random'):
        """生成单个行人"""
        if not self.walker_blueprints:
            self.load_walker_blueprints()
            
        # 随机选择行人类型
        walker_bp = random.choice(self.walker_blueprints)
        
        if transform is None:
            # 随机生成位置
            spawn_points = self.world.get_map().get_spawn_points()
            if spawn_points:
                transform = random.choice(spawn_points)
                # 调整高度为行人高度
                transform.location.z += 1.0
            else:
                transform = carla.Transform(
                    carla.Location(x=random.uniform(-50, 50), 
                                  y=random.uniform(-50, 50), 
                                  z=1.0)
                )
        
        # 生成行人
        walker = self.world.spawn_actor(walker_bp, transform)
        
        # 生成控制器
        controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
        controller = self.world.spawn_actor(controller_bp, carla.Transform(), walker)
        
        # 创建行人代理
        agent = PedestrianAgent(self.world, walker, controller)
        self.pedestrians.append(agent)
        
        print(f"[INFO] 生成行人 #{agent.id}，行为模式: {behavior}")
        return agent
    
    def spawn_pedestrians(self, count=10):
        """批量生成行人"""
        for i in range(count):
            self.spawn_pedestrian(behavior='random')
        print(f"[INFO] 共生成 {count} 个行人")
        
    def create_crossing_scenario(self, start_point, end_point, pedestrian_count=5):
        """创建过马路场景"""
        print(f"[场景] 创建过马路场景，行人数量: {pedestrian_count}")
        
        for i in range(pedestrian_count):
            # 在起点附近生成
            offset = random.uniform(-3, 3)
            spawn_point = carla.Transform(
                carla.Location(
                    x=start_point.x + offset,
                    y=start_point.y,
                    z=1.0
                )
            )
            
            agent = self.spawn_pedestrian(spawn_point)
            
            # 设置过马路目的地
            dest = carla.Location(
                x=end_point.x + offset,
                y=end_point.y,
                z=1.0
            )
            
            # 随机等待时间
            wait_time = random.uniform(0, 5)
            time.sleep(wait_time)
            
            agent.cross_road(start_point, dest)
            
    def create_crowd_scenario(self, center_point, radius=20, count=20):
        """创建人群场景"""
        print(f"[场景] 创建人群场景，中心: {center_point}, 人数: {count}")
        
        for i in range(count):
            # 在圆形区域内随机生成
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, radius)
            
            x = center_point.x + distance * math.cos(angle)
            y = center_point.y + distance * math.sin(angle)
            
            spawn_point = carla.Transform(
                carla.Location(x=x, y=y, z=1.0)
            )
            
            agent = self.spawn_pedestrian(spawn_point)
            
            # 随机目的地
            dest_angle = random.uniform(0, 2 * math.pi)
            dest_distance = random.uniform(10, 30)
            dest = carla.Location(
                x=center_point.x + dest_distance * math.cos(dest_angle),
                y=center_point.y + dest_distance * math.sin(dest_angle),
                z=1.0
            )
            
            agent.set_destination(dest)
    
    def create_queue_scenario(self, start_point, direction, count=10):
        """创建排队场景"""
        print(f"[场景] 创建排队场景，人数: {count}")
        
        for i in range(count):
            # 沿直线排列
            offset = i * 1.5  # 每人间隔1.5米
            
            spawn_point = carla.Transform(
                carla.Location(
                    x=start_point.x + offset * math.cos(direction),
                    y=start_point.y + offset * math.sin(direction),
                    z=1.0
                )
            )
            
            agent = self.spawn_pedestrian(spawn_point)
            
            # 设置前进目的地
            dest = carla.Location(
                x=start_point.x + (offset + 20) * math.cos(direction),
                y=start_point.y + (offset + 20) * math.sin(direction),
                z=1.0
            )
            
            # 依次启动，模拟排队
            time.sleep(random.uniform(0.5, 1.5))
            agent.set_destination(dest)
    
    def simulate_random_behavior(self, duration=60):
        """模拟随机行为"""
        print(f"[模拟] 开始随机行为模拟，持续时间: {duration}秒")
        self.running = True
        
        start_time = time.time()
        
        try:
            while self.running and (time.time() - start_time) < duration:
                for agent in self.pedestrians:
                    if agent.state == PedestrianState.IDLE:
                        # 随机选择新目的地
                        new_dest = carla.Location(
                            x=random.uniform(-100, 100),
                            y=random.uniform(-100, 100),
                            z=1.0
                        )
                        agent.set_destination(new_dest)
                        
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n[模拟] 随机行为模拟被中断")
            
    def update_pedestrians(self):
        """更新所有行人状态"""
        for agent in self.pedestrians:
            current_loc = agent.get_location()
            
            # 检查是否到达目的地
            if agent.destination and agent.state in [PedestrianState.WALKING, PedestrianState.CROSSING, PedestrianState.RUNNING]:
                distance = math.sqrt(
                    (current_loc.x - agent.destination.x)**2 +
                    (current_loc.y - agent.destination.y)**2
                )
                
                if distance < 1.0:
                    agent.state = PedestrianState.IDLE
                    if agent.controller:
                        agent.controller.stop()
    
    def remove_all_pedestrians(self):
        """移除所有行人"""
        print(f"[INFO] 移除 {len(self.pedestrians)} 个行人")
        for agent in self.pedestrians:
            agent.destroy()
        self.pedestrians.clear()
        
    def get_pedestrian_count(self):
        """获取当前行人数"""
        return len(self.pedestrians)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='行人行为模拟器')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--scenario', default='random',
                       choices=['random', 'crossing', 'crowd', 'queue'],
                       help='场景类型')
    parser.add_argument('--count', type=int, default=10, help='行人数量')
    parser.add_argument('--duration', type=int, default=60, help='模拟持续时间(秒)')
    
    args = parser.parse_args()
    
    simulator = PedestrianSimulator(args.host, args.port)
    
    try:
        if args.scenario == 'random':
            simulator.spawn_pedestrians(args.count)
            simulator.simulate_random_behavior(args.duration)
            
        elif args.scenario == 'crossing':
            simulator.create_crossing_scenario(
                carla.Location(x=0, y=-10, z=1.0),
                carla.Location(x=0, y=10, z=1.0),
                args.count
            )
            time.sleep(args.duration)
            
        elif args.scenario == 'crowd':
            simulator.create_crowd_scenario(
                carla.Location(x=0, y=0, z=0),
                radius=20,
                count=args.count
            )
            time.sleep(args.duration)
            
        elif args.scenario == 'queue':
            simulator.create_queue_scenario(
                carla.Location(x=-20, y=0, z=1.0),
                direction=0,  # 向东
                count=args.count
            )
            time.sleep(args.duration)
            
    except KeyboardInterrupt:
        print("\n[INFO] 程序被中断")
    finally:
        simulator.remove_all_pedestrians()


if __name__ == '__main__':
    main()
