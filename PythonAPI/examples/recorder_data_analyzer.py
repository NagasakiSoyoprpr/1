#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录数据分析工具
基于已有记录器数据进行分析

复现说明：
  1. 如何生成记录文件（recording文件）：
     方法一：使用 CARLA 自带的录制功能
       - 启动CARLA模拟器后，在Python终端执行：
         import carla
         client = carla.Client('localhost', 2000)
         client.start_recorder('recording.log')
         # ... 运行场景 ...
         client.stop_recorder()
       - 录制文件将保存为 recording.log

     方法二：使用 data_recorder.py 脚本（如果可用）
       python data_recorder.py --output recording.log --duration 60

     方法三：使用 CARLA 命令行参数启动时自动录制
       ./CarlaUE4.sh -CarlaRecorder=file.log

  2. 运行分析脚本：
     python recorder_data_analyzer.py --file recording.log                     # 分析记录文件
     python recorder_data_analyzer.py --file recording.log --output report.json  # 指定输出文件
  3. 参数说明：
     --file   : 记录文件路径（必填，支持 .log 和 .json 格式）
     --output : 输出报告路径（可选，默认自动生成带时间戳的文件名）
  4. 输出：JSON格式的分析报告，包含车辆轨迹分析和碰撞事件分析
"""

import json
import os
import argparse
from datetime import datetime


class RecorderDataAnalyzer:
    """记录数据分析器"""

    def __init__(self, recording_file=None):
        self.recording_file = recording_file
        self.data = None

    def load_recording(self, file_path):
        """加载记录文件"""
        if not os.path.exists(file_path):
            print(f"[错误] 文件不存在: {file_path}")
            return False

        try:
            # 尝试作为JSON格式加载
            with open(file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"[信息] 已加载记录文件(JSON): {file_path}")
            return True
        except json.JSONDecodeError:
            # 如果不是JSON，尝试作为CARLA log格式加载
            try:
                self.data = self._parse_carla_log(file_path)
                if self.data:
                    print(f"[信息] 已加载记录文件(CARLA Log): {file_path}")
                    return True
                else:
                    print(f"[错误] 无法解析记录文件: {file_path}")
                    return False
            except Exception as e:
                print(f"[错误] 加载失败: {e}")
                return False
        except Exception as e:
            print(f"[错误] 加载失败: {e}")
            return False

    def _parse_carla_log(self, file_path):
        """解析CARLA日志格式的记录文件"""
        try:
            frames = []
            events = []

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if 'frame' in entry:
                            frames.append(entry)
                        elif 'type' in entry:
                            events.append(entry)
                    except (json.JSONDecodeError, ValueError):
                        # 跳过无法解析的行
                        continue

            if frames or events:
                return {'frames': frames, 'events': events}
            return None
        except Exception as e:
            print(f"[警告] 解析CARLA日志失败: {e}")
            return None

    def analyze_vehicle_trajectory(self):
        """分析车辆轨迹"""
        if not self.data:
            return None

        positions = []
        frames = self.data.get('frames', [])

        for frame in frames:
            # 支持多种数据格式
            actors = frame.get('actors', [])
            for actor in actors:
                if isinstance(actor, dict):
                    type_id = actor.get('type_id', '')
                    if isinstance(type_id, str) and type_id.startswith('vehicle'):
                        pos = actor.get('location', {})
                        if isinstance(pos, dict):
                            positions.append((
                                pos.get('x', 0),
                                pos.get('y', 0),
                                pos.get('z', 0)
                            ))

        if not positions:
            return None

        # 计算总距离
        total_distance = 0
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i - 1][0]
            dy = positions[i][1] - positions[i - 1][1]
            dz = positions[i][2] - positions[i - 1][2]
            total_distance += (dx ** 2 + dy ** 2 + dz ** 2) ** 0.5

        return {
            'total_points': len(positions),
            'total_distance': round(total_distance, 2),
            'start_point': positions[0],
            'end_point': positions[-1]
        }

    def analyze_collision_events(self):
        """分析碰撞事件"""
        if not self.data:
            return None

        collisions = []
        events = self.data.get('events', [])

        for event in events:
            if isinstance(event, dict) and event.get('type') == 'collision':
                collisions.append({
                    'time': event.get('time', 0),
                    'actors': event.get('actors', []),
                    'intensity': event.get('intensity', 0)
                })

        return {
            'total_collisions': len(collisions),
            'collisions': collisions
        }

    def generate_report(self, output_file=None):
        """生成分析报告"""
        if not self.data:
            print("[错误] 没有加载数据")
            return

        if not output_file:
            output_file = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        report = {
            'generated_at': datetime.now().isoformat(),
            'source_file': self.recording_file,
            'trajectory_analysis': self.analyze_vehicle_trajectory(),
            'collision_analysis': self.analyze_collision_events()
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            print(f"[信息] 分析报告已保存: {output_file}")
        except Exception as e:
            print(f"[错误] 保存报告失败: {e}")

        return report


def main():
    parser = argparse.ArgumentParser(description='记录数据分析工具')
    parser.add_argument('--file', required=True,
                        help='记录文件路径（必填，支持 .log 和 .json 格式）')
    parser.add_argument('--output', default=None,
                        help='输出报告路径（可选，默认自动生成带时间戳的文件名）')

    args = parser.parse_args()

    try:
        analyzer = RecorderDataAnalyzer(args.file)
        if analyzer.load_recording(args.file):
            report = analyzer.generate_report(args.output)
            if report:
                # 打印摘要
                traj = report.get('trajectory_analysis')
                coll = report.get('collision_analysis')
                if traj:
                    print(f"\n[摘要] 轨迹点数: {traj['total_points']}，总距离: {traj['total_distance']}m")
                else:
                    print("\n[摘要] 未找到车辆轨迹数据")
                if coll:
                    print(f"[摘要] 碰撞事件: {coll['total_collisions']} 次")
                else:
                    print("[摘要] 未找到碰撞事件数据")
            else:
                print("[错误] 生成报告失败")
        else:
            print("[错误] 加载记录文件失败")
    except KeyboardInterrupt:
        print("\n[信息] 程序被中断")
    except Exception as e:
        print(f"[错误] 程序异常: {e}")


if __name__ == '__main__':
    main()
