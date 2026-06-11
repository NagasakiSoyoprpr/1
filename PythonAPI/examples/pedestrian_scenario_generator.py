#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行人测试场景生成器
基于已有行人系统生成各种测试场景

复现说明：
  1. 启动CARLA模拟器（推荐地图：Town03 或 Town01，因这些地图有较多人行横道和步行区域）
  2. 运行脚本：
     python pedestrian_scenario_generator.py --scenario crossing --count 5    # 过马路场景
     python pedestrian_scenario_generator.py --scenario crowd --count 20      # 人群场景
     python pedestrian_scenario_generator.py --scenario risk --count 3         # 碰撞风险场景
     python pedestrian_scenario_generator.py --scenario crossing --duration 60 # 自定义持续时间
  3. 参数说明：
     --host     : 模拟器主机地址（默认：localhost）
     --port     : 模拟器端口（默认：2000）
     --scenario : 场景类型，可选 crossing（过马路）/ crowd（人群）/ risk（碰撞风险），默认：crossing
     --count    : 行人数量（默认：5）
     --duration : 场景持续时间，单位秒（默认：30）
  4. 适用地图：Town01、Town03（其他地图也可运行，但行人位置可能需要调整）
  5. 行人位置会通过 world.debug 绘制可视化标记，方便在模拟器中观察
"""

import carla
import random
import math
import time
import argparse


class PedestrianScenarioGenerator:
    """行人测试场景生成器"""

    def __init__(self, host='localhost', port=2000):
        try:
            self.client = carla.Client(host, port)
            self.client.set_timeout(10.0)
            self.world = self.client.get_world()
            self.debug = self.world.debug
            self.pedestrians = []
            print("[初始化] 行人测试场景生成器已启动")
        except Exception as e:
            print(f"[错误] 初始化失败: {e}")
            raise

    def load_walker_blueprints(self):
        """加载行人蓝图"""
        try:
            blueprint_library = self.world.get_blueprint_library()
            walker_bps = blueprint_library.filter('walker.pedestrian.*')
            if not walker_bps:
                # 尝试更宽泛的匹配
                walker_bps = blueprint_library.filter('walker.*')
            if not walker_bps:
                print("[错误] 未找到任何行人蓝图")
                return []
            return walker_bps
        except Exception as e:
            print(f"[错误] 加载行人蓝图失败: {e}")
            return []

    def spawn_pedestrian(self, transform, behavior='random'):
        """生成单个行人"""
        try:
            walker_bps = self.load_walker_blueprints()
            if not walker_bps:
                print("[错误] 无可用行人蓝图，跳过生成")
                return None, None

            walker_bp = random.choice(walker_bps)

            walker = self.world.spawn_actor(walker_bp, transform)

            # 添加AI控制器
            controller_bp = self.world.get_blueprint_library().find('controller.ai.walker')
            if controller_bp is None:
                print("[错误] 未找到 walker AI 控制器蓝图")
                walker.destroy()
                return None, None

            controller = self.world.spawn_actor(controller_bp, carla.Transform(), walker)

            # 启动行人
            controller.start()

            self.pedestrians.append({'walker': walker, 'controller': controller})

            # 绘制行人位置标记
            self._draw_pedestrian_marker(walker, len(self.pedestrians))

            return walker, controller
        except Exception as e:
            print(f"[错误] 生成行人失败: {e}")
            return None, None

    def _draw_pedestrian_marker(self, walker, index):
        """使用debug绘制标记行人位置"""
        try:
            loc = walker.get_location()
            # 绘制行人脚下的圆圈标记
            color = carla.Color(255, 165, 0)  # 橙色

            # 绘制十字标记
            size = 0.5
            self.debug.draw_line(
                carla.Location(x=loc.x - size, y=loc.y, z=loc.z + 0.1),
                carla.Location(x=loc.x + size, y=loc.y, z=loc.z + 0.1),
                thickness=0.1, color=color, life_time=120.0
            )
            self.debug.draw_line(
                carla.Location(x=loc.x, y=loc.y - size, z=loc.z + 0.1),
                carla.Location(x=loc.x, y=loc.y + size, z=loc.z + 0.1),
                thickness=0.1, color=color, life_time=120.0
            )

            # 在行人头顶绘制编号
            self.debug.draw_string(
                carla.Location(x=loc.x, y=loc.y, z=loc.z + 2.5),
                f"P{index}",
                color=carla.Color(255, 255, 0),
                life_time=120.0
            )
        except Exception as e:
            print(f"[警告] 绘制行人标记失败: {e}")

    def _draw_area_marker(self, center_x, center_y, radius, label, color=None):
        """绘制区域标记"""
        try:
            if color is None:
                color = carla.Color(0, 255, 255)

            # 绘制圆形区域（用多边形近似）
            points = 24
            for i in range(points):
                angle1 = 2 * math.pi * i / points
                angle2 = 2 * math.pi * (i + 1) / points
                p1 = carla.Location(
                    x=center_x + radius * math.cos(angle1),
                    y=center_y + radius * math.sin(angle1),
                    z=0.5
                )
                p2 = carla.Location(
                    x=center_x + radius * math.cos(angle2),
                    y=center_y + radius * math.sin(angle2),
                    z=0.5
                )
                self.debug.draw_line(p1, p2, thickness=0.1, color=color, life_time=120.0)

            # 绘制区域标签
            self.debug.draw_string(
                carla.Location(x=center_x, y=center_y, z=5.0),
                label,
                color=color,
                life_time=120.0
            )
        except Exception as e:
            print(f"[警告] 绘制区域标记失败: {e}")

    def generate_crossing_scenario(self, road_width=10, pedestrian_count=5):
        """生成过马路测试场景"""
        print(f"[场景] 生成过马路场景，道路宽度: {road_width}m，行人: {pedestrian_count}")

        # 绘制道路区域标记
        self._draw_area_marker(0, 0, road_width / 2 + 2, "Crossing Zone",
                               carla.Color(255, 0, 0))

        for i in range(pedestrian_count):
            try:
                x = random.uniform(-road_width / 2, road_width / 2)
                y = random.choice([-5, 5])

                transform = carla.Transform(
                    carla.Location(x=x, y=y, z=1.0)
                )

                walker, controller = self.spawn_pedestrian(transform)
                if walker is None or controller is None:
                    print(f"[警告] 行人 #{i+1} 生成失败，跳过")
                    continue

                # 设置过马路目标
                target = carla.Location(x=x, y=-y, z=1.0)
                controller.go_to_location(target)
                controller.set_max_speed(1.4)

                # 绘制行人目标路径
                self.debug.draw_line(
                    carla.Location(x=x, y=y, z=1.5),
                    carla.Location(x=x, y=-y, z=1.5),
                    thickness=0.05, color=carla.Color(0, 255, 255), life_time=60.0
                )

                print(f"  行人 #{i+1} 从 ({x:.1f}, {y:.1f}) 到 ({x:.1f}, {-y:.1f})")
            except Exception as e:
                print(f"[错误] 生成行人 #{i+1} 失败: {e}")

    def generate_crowd_scenario(self, center, radius=20, count=20):
        """生成人群测试场景"""
        print(f"[场景] 生成人群场景，中心: ({center.x}, {center.y})，半径: {radius}m，人数: {count}")

        # 绘制人群区域标记
        self._draw_area_marker(center.x, center.y, radius, f"Crowd ({count})",
                               carla.Color(0, 255, 0))

        for i in range(count):
            try:
                angle = random.uniform(0, 2 * math.pi)
                distance = random.uniform(0, radius)

                x = center.x + distance * math.cos(angle)
                y = center.y + distance * math.sin(angle)

                transform = carla.Transform(
                    carla.Location(x=x, y=y, z=1.0)
                )

                walker, controller = self.spawn_pedestrian(transform)
                if walker is None or controller is None:
                    print(f"[警告] 行人 #{i+1} 生成失败，跳过")
                    continue

                # 随机移动目标
                target_angle = random.uniform(0, 2 * math.pi)
                target_dist = random.uniform(10, 30)
                target = carla.Location(
                    x=center.x + target_dist * math.cos(target_angle),
                    y=center.y + target_dist * math.sin(target_angle),
                    z=1.0
                )

                controller.go_to_location(target)
                controller.set_max_speed(random.uniform(1.0, 2.0))
            except Exception as e:
                print(f"[错误] 生成行人 #{i+1} 失败: {e}")

    def generate_collision_risk_scenario(self, vehicle_path, pedestrian_count=3):
        """生成碰撞风险测试场景"""
        print(f"[场景] 生成碰撞风险场景，行人: {pedestrian_count}")

        # 绘制车辆路径
        try:
            self.debug.draw_line(
                vehicle_path[0] + carla.Location(z=0.5),
                vehicle_path[1] + carla.Location(z=0.5),
                thickness=0.2, color=carla.Color(255, 0, 0), life_time=120.0
            )
            self.debug.draw_string(
                carla.Location(
                    x=(vehicle_path[0].x + vehicle_path[1].x) / 2,
                    y=(vehicle_path[0].y + vehicle_path[1].y) / 2,
                    z=3.0
                ),
                "Vehicle Path",
                color=carla.Color(255, 0, 0),
                life_time=120.0
            )
        except Exception as e:
            print(f"[警告] 绘制车辆路径失败: {e}")

        for i in range(pedestrian_count):
            try:
                t = random.uniform(0.2, 0.8)
                x = vehicle_path[0].x + (vehicle_path[1].x - vehicle_path[0].x) * t
                y = vehicle_path[0].y + (vehicle_path[1].y - vehicle_path[0].y) * t

                offset = random.uniform(-3, 3)
                x += offset

                transform = carla.Transform(
                    carla.Location(x=x, y=y, z=1.0)
                )

                walker, controller = self.spawn_pedestrian(transform)
                if walker is None or controller is None:
                    print(f"[警告] 风险行人 #{i+1} 生成失败，跳过")
                    continue

                # 让行人停留在原地或缓慢移动
                if random.choice([True, False]):
                    controller.set_max_speed(0.5)
                else:
                    controller.set_max_speed(0)

                # 绘制风险标记（红色警告）
                try:
                    loc = walker.get_location()
                    self.debug.draw_box(
                        carla.BoundingBox(
                            carla.Location(x=loc.x, y=loc.y, z=loc.z + 1.0),
                            carla.Vector3(x=0.5, y=0.5, z=1.0)
                        ),
                        carla.Rotation(),
                        thickness=0.1,
                        color=carla.Color(255, 0, 0),
                        life_time=120.0
                    )
                except Exception:
                    pass

                print(f"  风险行人 #{i+1} 位置: ({x:.1f}, {y:.1f})")
            except Exception as e:
                print(f"[错误] 生成风险行人 #{i+1} 失败: {e}")

    def update_pedestrian_markers(self):
        """更新行人位置标记（周期性调用）"""
        try:
            for i, p in enumerate(self.pedestrians):
                if p['walker'].is_alive:
                    loc = p['walker'].get_location()
                    color = carla.Color(255, 165, 0)
                    size = 0.3
                    self.debug.draw_line(
                        carla.Location(x=loc.x - size, y=loc.y, z=loc.z + 0.1),
                        carla.Location(x=loc.x + size, y=loc.y, z=loc.z + 0.1),
                        thickness=0.1, color=color, life_time=0.2
                    )
                    self.debug.draw_line(
                        carla.Location(x=loc.x, y=loc.y - size, z=loc.z + 0.1),
                        carla.Location(x=loc.x, y=loc.y + size, z=loc.z + 0.1),
                        thickness=0.1, color=color, life_time=0.2
                    )
        except Exception:
            pass

    def cleanup(self):
        """清理所有行人"""
        print(f"[清理] 移除 {len(self.pedestrians)} 个行人")
        for p in self.pedestrians:
            try:
                if p['controller'].is_alive:
                    p['controller'].stop()
                    p['controller'].destroy()
            except Exception as e:
                print(f"[警告] 销毁控制器失败: {e}")
            try:
                if p['walker'].is_alive:
                    p['walker'].destroy()
            except Exception as e:
                print(f"[警告] 销毁行人失败: {e}")
        self.pedestrians.clear()


def main():
    parser = argparse.ArgumentParser(description='行人测试场景生成器')
    parser.add_argument('--host', default='localhost', help='主机地址')
    parser.add_argument('--port', type=int, default=2000, help='端口')
    parser.add_argument('--scenario', default='crossing',
                        choices=['crossing', 'crowd', 'risk'],
                        help='场景类型: crossing(过马路) / crowd(人群) / risk(碰撞风险)')
    parser.add_argument('--count', type=int, default=5, help='行人数量')
    parser.add_argument('--duration', type=int, default=30, help='持续时间(秒)')

    args = parser.parse_args()

    generator = None
    try:
        generator = PedestrianScenarioGenerator(args.host, args.port)

        if args.scenario == 'crossing':
            generator.generate_crossing_scenario(pedestrian_count=args.count)
        elif args.scenario == 'crowd':
            generator.generate_crowd_scenario(
                carla.Location(x=0, y=0, z=0),
                count=args.count
            )
        elif args.scenario == 'risk':
            generator.generate_collision_risk_scenario(
                [carla.Location(x=-50, y=0, z=0), carla.Location(x=50, y=0, z=0)],
                pedestrian_count=args.count
            )

        print(f"\n[运行] 场景运行中，持续 {args.duration} 秒...")
        print("[运行] 行人位置已通过debug标记可视化，可在模拟器中观察")

        # 运行期间周期性更新标记
        start_time = time.time()
        while time.time() - start_time < args.duration:
            generator.update_pedestrian_markers()
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[中断] 用户中断")
    except Exception as e:
        print(f"[错误] 程序异常: {e}")
    finally:
        if generator is not None:
            generator.cleanup()
        print("[完成] 场景结束")


if __name__ == '__main__':
    main()

