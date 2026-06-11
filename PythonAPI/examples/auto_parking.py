#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
车辆自动泊车系统
实现车辆的自动平行泊车和垂直泊车功能

复现说明：
  1. 启动CARLA模拟器（推荐地图：Town03 或 Town05，因这些地图有较宽的道路和停车场区域）
  2. 运行脚本：
     python auto_parking.py --type parallel        # 平行泊车
     python auto_parking.py --type perpendicular    # 垂直泊车
     python auto_parking.py --host localhost --port 2000 --type parallel
  3. 参数说明：
     --host   : 模拟器主机地址（默认：localhost）
     --port   : 模拟器端口（默认：2000）
     --type   : 泊车类型，可选 parallel（平行泊车）或 perpendicular（垂直泊车），默认：parallel
  4. 适用地图：Town03、Town05（其他地图可能因停车位坐标不同需要调整）
  5. 脚本会自动生成车辆、检测停车位、执行泊车动作，并将spectator视角切换到泊车位置
"""

import carla
import math
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
        try:
            blueprint_library = self.world.get_blueprint_library()

            # 尝试首选蓝图，失败则使用备用蓝图
            vehicle_bp_list = blueprint_library.filter('vehicle.tesla.model3')
            if vehicle_bp_list:
                vehicle_bp = vehicle_bp_list[0]
            else:
                vehicle_bp_list = blueprint_library.filter('vehicle.*')
                if vehicle_bp_list:
                    vehicle_bp = vehicle_bp_list[0]
                    print(f"[WARNING] 未找到 vehicle.tesla.model3，使用备用蓝图: {vehicle_bp.id}")
                else:
                    print("[ERROR] 未找到任何车辆蓝图")
                    return None

            if transform is None:
                transform = carla.Transform(
                    carla.Location(x=50, y=10, z=0.5),
                    carla.Rotation(yaw=0)
                )

            self.vehicle = self.world.spawn_actor(vehicle_bp, transform)
            print(f"[INFO] 车辆已生成: {self.vehicle.type_id}")
            return self.vehicle
        except Exception as e:
            print(f"[ERROR] 生成车辆失败: {e}")
            return None

    def calculate_parking_trajectory(self, start_pos, end_pos, parking_type='parallel'):
        """计算泊车轨迹"""
        trajectory = []

        if parking_type == 'parallel':
            mid_point = carla.Location(
                x=start_pos.location.x + 5,
                y=start_pos.location.y,
                z=start_pos.location.z
            )
            trajectory.append(('drive_forward', mid_point))
            trajectory.append(('reverse_park', end_pos.location))

        elif parking_type == 'perpendicular':
            mid_point = carla.Location(
                x=start_pos.location.x + 3,
                y=start_pos.location.y,
                z=start_pos.location.z
            )
            trajectory.append(('drive_forward', mid_point))

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

            try:
                if action == 'drive_forward':
                    self._drive_forward(target)
                elif action == 'reverse_park':
                    self._reverse_park(target)
                elif action == 'turn_in':
                    self._turn_in(target)
                elif action == 'final_adjust':
                    self._final_adjust(target)
            except Exception as e:
                print(f"[ERROR] 执行动作 {action} 失败: {e}")
                break

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
        control.steer = 0.3

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
            (loc1.x - loc2.x) ** 2 +
            (loc1.y - loc2.y) ** 2 +
            (loc1.z - loc2.z) ** 2
        )

    def detect_parking_spot(self):
        """检测可用停车位"""
        parking_spots = []

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

    def switch_spectator_to_parking(self, target_transform):
        """将spectator视角切换到泊车位置附近"""
        try:
            spectator = self.world.get_spectator()
            # 将spectator设置在停车位附近的高处俯瞰
            spectator_transform = carla.Transform(
                carla.Location(
                    x=target_transform.location.x + 10,
                    y=target_transform.location.y - 15,
                    z=20
                ),
                carla.Rotation(pitch=-30, yaw=-45)
            )
            spectator.set_transform(spectator_transform)
            print("[INFO] 已切换spectator视角到泊车位置")
        except Exception as e:
            print(f"[WARNING] 切换spectator视角失败: {e}")

    def draw_parking_spot_debug(self, spot_transform, spot_type):
        """使用debug绘制标记停车位"""
        try:
            debug = self.world.debug
            loc = spot_transform.location
            color = carla.Color(0, 255, 255)  # 青色

            # 绘制停车位四个角
            size = 3.0 if spot_type == 'parallel' else 2.5
            corners = [
                carla.Location(x=loc.x - size, y=loc.y - size * 0.5, z=loc.z + 0.1),
                carla.Location(x=loc.x + size, y=loc.y - size * 0.5, z=loc.z + 0.1),
                carla.Location(x=loc.x + size, y=loc.y + size * 0.5, z=loc.z + 0.1),
                carla.Location(x=loc.x - size, y=loc.y + size * 0.5, z=loc.z + 0.1),
            ]

            for i in range(4):
                debug.draw_line(
                    corners[i], corners[(i + 1) % 4],
                    thickness=0.1, color=color, life_time=120.0
                )

            # 在停车位中心绘制标记
            debug.draw_point(
                loc + carla.Location(z=1.0),
                size=0.3, color=carla.Color(255, 255, 0), life_time=120.0
            )
            debug.draw_string(
                loc + carla.Location(z=3.0),
                f"Parking: {spot_type}",
                color=carla.Color(255, 255, 255),
                life_time=120.0
            )
            print(f"[INFO] 已绘制停车位标记: {spot_type}")
        except Exception as e:
            print(f"[WARNING] 绘制停车位标记失败: {e}")

    def cleanup(self):
        """清理资源"""
        try:
            if self.vehicle and self.vehicle.is_alive:
                self.vehicle.destroy()
                print("[INFO] 车辆已销毁")
        except Exception as e:
            print(f"[WARNING] 销毁车辆失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='自动泊车系统')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--type', default='parallel',
                        choices=['parallel', 'perpendicular'],
                        help='泊车类型: parallel(平行泊车) 或 perpendicular(垂直泊车)')

    args = parser.parse_args()

    parking = None
    try:
        parking = AutoParking(args.host, args.port)

        # 生成车辆
        start_transform = carla.Transform(
            carla.Location(x=40, y=10, z=0.5),
            carla.Rotation(yaw=0)
        )
        vehicle = parking.spawn_vehicle(start_transform)
        if vehicle is None:
            print("[ERROR] 车辆生成失败，退出")
            return

        # 检测停车位
        spots = parking.detect_parking_spot()
        if spots:
            # 根据用户选择的泊车类型匹配停车位
            target_spot = None
            for spot_type, spot_transform in spots:
                if spot_type == args.type:
                    target_spot = (spot_type, spot_transform)
                    break

            # 如果没有精确匹配，使用第一个
            if target_spot is None:
                target_spot = spots[0]
                print(f"[WARNING] 未找到 {args.type} 类型停车位，使用第一个可用停车位")

            spot_type, spot_transform = target_spot
            print(f"[INFO] 检测到停车位: {spot_type}")

            # 绘制停车位标记
            parking.draw_parking_spot_debug(spot_transform, spot_type)

            # 切换spectator视角到泊车位置
            parking.switch_spectator_to_parking(spot_transform)

            # 计算并执行泊车轨迹
            trajectory = parking.calculate_parking_trajectory(
                start_transform, spot_transform, args.type
            )
            parking.execute_parking(trajectory)
        else:
            print("[WARNING] 未检测到可用停车位")

    except KeyboardInterrupt:
        print("\n[INFO] 程序被中断")
    except Exception as e:
        print(f"[ERROR] 程序异常: {e}")
    finally:
        if parking is not None:
            parking.cleanup()


if __name__ == '__main__':
    main()
