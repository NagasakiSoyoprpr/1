#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交通灯测试工具
基于已有交通灯系统进行功能测试和验证

复现说明：
  1. 启动CARLA模拟器（推荐地图：Town01、Town02 或 Town03，这些地图有交通灯系统）
  2. 运行脚本：
     python traffic_light_tester.py                    # 运行所有测试
     python traffic_light_tester.py --test states       # 仅测试交通灯状态
     python traffic_light_tester.py --test transition   # 仅测试状态转换
     python traffic_light_tester.py --test manual      # 仅测试手动控制
  3. 参数说明：
     --host : 模拟器主机地址（默认：localhost）
     --port : 模拟器端口（默认：2000）
     --test : 测试类型，可选 all / states / transition / manual，默认：all
  4. 适用地图：Town01、Town02、Town03（Town04+ 也支持，但交通灯配置可能不同）
  5. transition 测试会持续30秒监控交通灯状态变化
  6. manual 测试会临时改变交通灯状态，测试完成后会恢复原始状态
"""

import carla
import time
import argparse


class TrafficLightTester:
    """交通灯测试器"""

    def __init__(self, host='localhost', port=2000):
        try:
            self.client = carla.Client(host, port)
            self.client.set_timeout(10.0)
            self.world = self.client.get_world()
            self.traffic_lights = []
            self.debug = self.world.debug
            print("[初始化] 交通灯测试工具已启动")
        except Exception as e:
            print(f"[错误] 初始化失败: {e}")
            raise

    def get_all_traffic_lights(self):
        """获取所有交通灯"""
        try:
            self.traffic_lights = self.world.get_actors().filter('traffic.traffic_light')
            print(f"[信息] 发现 {len(self.traffic_lights)} 个交通灯")
            return self.traffic_lights
        except Exception as e:
            print(f"[错误] 获取交通灯失败: {e}")
            self.traffic_lights = []
            return self.traffic_lights

    def test_traffic_light_states(self):
        """测试交通灯状态切换"""
        print("\n[测试] 交通灯状态测试")
        self.get_all_traffic_lights()

        if not self.traffic_lights:
            print("[警告] 未找到交通灯")
            return

        for i, tl in enumerate(self.traffic_lights[:5]):
            try:
                print(f"\n  交通灯 #{i + 1} (ID: {tl.id}):")
                state = tl.get_state()
                print(f"    当前状态: {state}")
                print(f"    绿灯时间: {tl.get_green_time():.1f}s")
                print(f"    黄灯时间: {tl.get_yellow_time():.1f}s")
                print(f"    红灯时间: {tl.get_red_time():.1f}s")
                print(f"    冻结状态: {tl.is_frozen()}")

                # 绘制交通灯位置标记
                self._draw_traffic_light_marker(tl, i + 1)
            except Exception as e:
                print(f"  [错误] 读取交通灯 #{i + 1} 状态失败: {e}")

    def test_state_transition(self, duration=30):
        """测试状态转换"""
        print(f"\n[测试] 交通灯状态转换测试，持续 {duration} 秒")
        self.get_all_traffic_lights()

        if not self.traffic_lights:
            print("[警告] 未找到交通灯")
            return

        tl = self.traffic_lights[0]
        start_time = time.time()
        state_changes = []

        try:
            last_state = tl.get_state()
        except Exception as e:
            print(f"[错误] 获取交通灯状态失败: {e}")
            return

        print(f"  监控交通灯 #{tl.id} 的状态变化...")

        try:
            while time.time() - start_time < duration:
                try:
                    current_state = tl.get_state()
                    if current_state != last_state:
                        change_time = time.time() - start_time
                        state_changes.append({
                            'time': change_time,
                            'from': str(last_state),
                            'to': str(current_state)
                        })
                        print(f"    [{change_time:.1f}s] {last_state} -> {current_state}")
                        last_state = current_state
                except Exception as e:
                    print(f"  [警告] 获取状态失败: {e}")
                time.sleep(0.1)

        except KeyboardInterrupt:
            pass

        print(f"\n[结果] 共检测到 {len(state_changes)} 次状态切换")
        return state_changes

    def test_manual_control(self):
        """测试手动控制"""
        print("\n[测试] 交通灯手动控制测试")
        self.get_all_traffic_lights()

        if not self.traffic_lights:
            print("[警告] 未找到交通灯")
            return

        tl = self.traffic_lights[0]

        try:
            original_state = tl.get_state()
            print(f"  原始状态: {original_state}")

            # 测试设置为红灯
            tl.set_state(carla.TrafficLightState.Red)
            time.sleep(0.1)
            print(f"  设置为红灯: {tl.get_state()}")
            time.sleep(2)

            # 测试设置为绿灯
            tl.set_state(carla.TrafficLightState.Green)
            time.sleep(0.1)
            print(f"  设置为绿灯: {tl.get_state()}")
            time.sleep(2)

            # 恢复原始状态
            tl.set_state(original_state)
            time.sleep(0.1)
            print(f"  恢复原始状态: {tl.get_state()}")
        except Exception as e:
            print(f"[错误] 手动控制测试失败: {e}")

    def _draw_traffic_light_marker(self, tl, index):
        """使用debug绘制交通灯位置标记"""
        try:
            transform = tl.get_transform()
            loc = transform.location

            # 根据状态选择颜色
            state = tl.get_state()
            if state == carla.TrafficLightState.Green:
                color = carla.Color(0, 255, 0)
            elif state == carla.TrafficLightState.Yellow:
                color = carla.Color(255, 255, 0)
            elif state == carla.TrafficLightState.Red:
                color = carla.Color(255, 0, 0)
            else:
                color = carla.Color(128, 128, 128)

            # 绘制交通灯位置标记
            self.debug.draw_point(
                loc + carla.Location(z=0.5),
                size=0.3,
                color=color,
                life_time=60.0
            )

            # 绘制标签
            self.debug.draw_string(
                loc + carla.Location(z=3.0),
                f"TL#{index} [{str(state)}]",
                color=color,
                life_time=60.0
            )
        except Exception as e:
            print(f"  [警告] 绘制交通灯标记失败: {e}")

    def generate_test_report(self):
        """生成测试报告"""
        self.get_all_traffic_lights()

        report = {
            'total_traffic_lights': len(self.traffic_lights),
            'traffic_lights': []
        }

        for tl in self.traffic_lights:
            try:
                report['traffic_lights'].append({
                    'id': tl.id,
                    'state': str(tl.get_state()),
                    'green_time': tl.get_green_time(),
                    'yellow_time': tl.get_yellow_time(),
                    'red_time': tl.get_red_time(),
                    'frozen': tl.is_frozen()
                })
            except Exception as e:
                print(f"[警告] 获取交通灯 {tl.id} 信息失败: {e}")

        return report


def main():
    parser = argparse.ArgumentParser(description='交通灯测试工具')
    parser.add_argument('--host', default='localhost', help='主机地址')
    parser.add_argument('--port', type=int, default=2000, help='端口')
    parser.add_argument('--test', default='all',
                        choices=['all', 'states', 'transition', 'manual'],
                        help='测试类型: all(全部) / states(状态) / transition(状态转换) / manual(手动控制)')

    args = parser.parse_args()

    tester = None
    try:
        tester = TrafficLightTester(args.host, args.port)

        if args.test == 'all' or args.test == 'states':
            tester.test_traffic_light_states()

        if args.test == 'all' or args.test == 'transition':
            tester.test_state_transition(duration=30)

        if args.test == 'all' or args.test == 'manual':
            tester.test_manual_control()

        print("\n[完成] 测试结束")

    except KeyboardInterrupt:
        print("\n[中断] 用户中断")
    except Exception as e:
        print(f"[错误] 程序异常: {e}")


if __name__ == '__main__':
    main()
