#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能监控与优化工具
监控模拟器运行性能，包括FPS、延迟、内存使用等，并提供优化建议
"""

import carla
import time
import psutil
import os
import json
from datetime import datetime
import argparse
from collections import deque
import threading


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, host='localhost', port=2000):
        """初始化性能监控器"""
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        
        self.running = False
        self.monitor_thread = None
        self.stats_history = deque(maxlen=1000)
        
        # 性能阈值
        self.fps_threshold = 30.0
        self.latency_threshold = 50.0  # ms
        self.memory_threshold = 80.0  # %
        
        # 进程信息
        self.process = psutil.Process(os.getpid())
        
        print("[INFO] 性能监控器已初始化")
        
    def get_system_stats(self):
        """获取系统统计信息"""
        stats = {
            'timestamp': time.time(),
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_used_gb': psutil.virtual_memory().used / (1024**3),
            'memory_available_gb': psutil.virtual_memory().available / (1024**3),
            'disk_usage_percent': psutil.disk_usage('/').percent
        }
        return stats
        
    def get_simulator_stats(self):
        """获取模拟器统计信息"""
        try:
            # 获取世界设置
            settings = self.world.get_settings()
            
            # 获取演员数量
            actors = self.world.get_actors()
            vehicle_count = len(actors.filter('vehicle.*'))
            pedestrian_count = len(actors.filter('walker.*'))
            sensor_count = len(actors.filter('sensor.*'))
            
            stats = {
                'actor_count': len(actors),
                'vehicle_count': vehicle_count,
                'pedestrian_count': pedestrian_count,
                'sensor_count': sensor_count,
                'synchronous_mode': settings.synchronous_mode,
                'fixed_delta_seconds': settings.fixed_delta_seconds
            }
            return stats
        except Exception as e:
            print(f"[ERROR] 获取模拟器统计信息失败: {e}")
            return {}
            
    def measure_frame_time(self, iterations=10):
        """测量帧时间"""
        frame_times = []
        
        for _ in range(iterations):
            start = time.time()
            self.world.tick() if self.world.get_settings().synchronous_mode else time.sleep(0.01)
            end = time.time()
            frame_times.append((end - start) * 1000)  # 转换为毫秒
            
        avg_frame_time = sum(frame_times) / len(frame_times)
        fps = 1000.0 / avg_frame_time if avg_frame_time > 0 else 0
        
        return {
            'avg_frame_time_ms': avg_frame_time,
            'min_frame_time_ms': min(frame_times),
            'max_frame_time_ms': max(frame_times),
            'fps': fps
        }
        
    def measure_network_latency(self, iterations=5):
        """测量网络延迟"""
        latencies = []
        
        for _ in range(iterations):
            start = time.time()
            self.client.get_server_version()
            end = time.time()
            latencies.append((end - start) * 1000)  # 转换为毫秒
            
        return {
            'avg_latency_ms': sum(latencies) / len(latencies),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies)
        }
        
    def collect_stats(self):
        """收集所有统计信息"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_stats(),
            'simulator': self.get_simulator_stats()
        }
        
        # 尝试测量帧时间（仅在同步模式下）
        if self.world.get_settings().synchronous_mode:
            stats['frame'] = self.measure_frame_time()
        else:
            stats['network'] = self.measure_network_latency()
            
        self.stats_history.append(stats)
        return stats
        
    def check_performance_issues(self, stats):
        """检查性能问题"""
        issues = []
        
        # 检查FPS
        if 'frame' in stats and stats['frame']['fps'] < self.fps_threshold:
            issues.append({
                'type': 'low_fps',
                'severity': 'warning',
                'message': f"FPS过低: {stats['frame']['fps']:.1f} (阈值: {self.fps_threshold})",
                'suggestion': '考虑减少演员数量或降低传感器分辨率'
            })
            
        # 检查内存使用
        if stats['system']['memory_percent'] > self.memory_threshold:
            issues.append({
                'type': 'high_memory',
                'severity': 'warning',
                'message': f"内存使用率高: {stats['system']['memory_percent']:.1f}%",
                'suggestion': '考虑重启模拟器或释放资源'
            })
            
        # 检查网络延迟
        if 'network' in stats and stats['network']['avg_latency_ms'] > self.latency_threshold:
            issues.append({
                'type': 'high_latency',
                'severity': 'info',
                'message': f"网络延迟高: {stats['network']['avg_latency_ms']:.1f}ms",
                'suggestion': '检查网络连接或降低数据传输量'
            })
            
        # 检查演员数量
        if stats['simulator'].get('actor_count', 0) > 200:
            issues.append({
                'type': 'too_many_actors',
                'severity': 'warning',
                'message': f"演员数量过多: {stats['simulator']['actor_count']}",
                'suggestion': '考虑减少车辆或行人数量'
            })
            
        return issues
        
    def print_stats(self, stats):
        """打印统计信息"""
        print("\n" + "="*60)
        print("性能监控报告")
        print("="*60)
        print(f"时间: {stats['timestamp']}")
        
        # 系统信息
        sys_stats = stats['system']
        print(f"\n[系统]")
        print(f"  CPU使用率: {sys_stats['cpu_percent']:.1f}%")
        print(f"  内存使用: {sys_stats['memory_percent']:.1f}% "
              f"({sys_stats['memory_used_gb']:.2f} GB / "
              f"{sys_stats['memory_available_gb']:.2f} GB 可用)")
        print(f"  磁盘使用: {sys_stats['disk_usage_percent']:.1f}%")
        
        # 模拟器信息
        sim_stats = stats['simulator']
        print(f"\n[模拟器]")
        print(f"  总演员数: {sim_stats.get('actor_count', 0)}")
        print(f"  车辆数: {sim_stats.get('vehicle_count', 0)}")
        print(f"  行人数: {sim_stats.get('pedestrian_count', 0)}")
        print(f"  传感器数: {sim_stats.get('sensor_count', 0)}")
        print(f"  同步模式: {sim_stats.get('synchronous_mode', False)}")
        
        # 帧信息
        if 'frame' in stats:
            frame_stats = stats['frame']
            print(f"\n[帧性能]")
            print(f"  FPS: {frame_stats['fps']:.1f}")
            print(f"  平均帧时间: {frame_stats['avg_frame_time_ms']:.2f} ms")
            print(f"  最小帧时间: {frame_stats['min_frame_time_ms']:.2f} ms")
            print(f"  最大帧时间: {frame_stats['max_frame_time_ms']:.2f} ms")
            
        # 网络信息
        if 'network' in stats:
            net_stats = stats['network']
            print(f"\n[网络]")
            print(f"  平均延迟: {net_stats['avg_latency_ms']:.2f} ms")
            print(f"  最小延迟: {net_stats['min_latency_ms']:.2f} ms")
            print(f"  最大延迟: {net_stats['max_latency_ms']:.2f} ms")
            
        # 性能问题
        issues = self.check_performance_issues(stats)
        if issues:
            print(f"\n[⚠️  性能警告]")
            for issue in issues:
                print(f"  [{issue['severity'].upper()}] {issue['message']}")
                print(f"    建议: {issue['suggestion']}")
        else:
            print(f"\n[✅ 性能良好]")
            
        print("="*60 + "\n")
        
    def start_monitoring(self, interval=5.0):
        """启动监控线程"""
        self.running = True
        
        def monitor_loop():
            while self.running:
                stats = self.collect_stats()
                self.print_stats(stats)
                time.sleep(interval)
                
        self.monitor_thread = threading.Thread(target=monitor_loop)
        self.monitor_thread.start()
        print(f"[INFO] 性能监控已启动，间隔: {interval}秒")
        
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        print("[INFO] 性能监控已停止")
        
    def generate_report(self, filename=None):
        """生成性能报告"""
        if not filename:
            filename = f'performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            
        # 计算统计数据
        if not self.stats_history:
            print("[WARNING] 没有统计数据")
            return
            
        fps_values = []
        memory_values = []
        latency_values = []
        
        for stats in self.stats_history:
            if 'frame' in stats:
                fps_values.append(stats['frame']['fps'])
            memory_values.append(stats['system']['memory_percent'])
            if 'network' in stats:
                latency_values.append(stats['network']['avg_latency_ms'])
                
        report = {
            'generated_at': datetime.now().isoformat(),
            'sample_count': len(self.stats_history),
            'summary': {
                'avg_fps': sum(fps_values) / len(fps_values) if fps_values else 0,
                'min_fps': min(fps_values) if fps_values else 0,
                'max_fps': max(fps_values) if fps_values else 0,
                'avg_memory_percent': sum(memory_values) / len(memory_values),
                'max_memory_percent': max(memory_values),
                'avg_latency_ms': sum(latency_values) / len(latency_values) if latency_values else 0,
                'max_latency_ms': max(latency_values) if latency_values else 0
            },
            'samples': list(self.stats_history)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"[INFO] 性能报告已保存: {filename}")
        return filename
        
    def get_optimization_suggestions(self):
        """获取优化建议"""
        suggestions = []
        
        # 获取最新统计
        if not self.stats_history:
            return ["请先运行监控以获取数据"]
            
        latest = self.stats_history[-1]
        
        # 基于演员数量的建议
        actor_count = latest['simulator'].get('actor_count', 0)
        if actor_count > 200:
            suggestions.append("演员数量过多，建议减少车辆或行人数量")
        elif actor_count > 100:
            suggestions.append("演员数量较多，可考虑优化")
            
        # 基于内存的建议
        memory_percent = latest['system']['memory_percent']
        if memory_percent > 80:
            suggestions.append("内存使用率过高，建议重启模拟器")
        elif memory_percent > 60:
            suggestions.append("内存使用率中等，注意监控")
            
        # 基于FPS的建议
        if 'frame' in latest:
            fps = latest['frame']['fps']
            if fps < 20:
                suggestions.append("FPS过低，建议降低画质或减少传感器")
            elif fps < 30:
                suggestions.append("FPS偏低，可考虑优化设置")
                
        # 基于传感器的建议
        sensor_count = latest['simulator'].get('sensor_count', 0)
        if sensor_count > 10:
            suggestions.append("传感器数量较多，建议减少不必要的传感器")
            
        if not suggestions:
            suggestions.append("当前性能良好，无需特别优化")
            
        return suggestions


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='性能监控与优化工具')
    parser.add_argument('--host', default='localhost', help='模拟器主机地址')
    parser.add_argument('--port', type=int, default=2000, help='模拟器端口')
    parser.add_argument('--interval', type=float, default=5.0, help='监控间隔(秒)')
    parser.add_argument('--duration', type=int, default=60, help='监控时长(秒)')
    
    args = parser.parse_args()
    
    monitor = PerformanceMonitor(args.host, args.port)
    
    try:
        print(f"[INFO] 开始性能监控，持续 {args.duration} 秒")
        print("[INFO] 按 Ctrl+C 提前停止")
        
        monitor.start_monitoring(args.interval)
        
        # 运行指定时长
        time.sleep(args.duration)
        
        monitor.stop_monitoring()
        
        # 生成报告
        monitor.generate_report()
        
        # 打印优化建议
        print("\n[优化建议]")
        for i, suggestion in enumerate(monitor.get_optimization_suggestions(), 1):
            print(f"  {i}. {suggestion}")
            
    except KeyboardInterrupt:
        print("\n[INFO] 监控被中断")
        monitor.stop_monitoring()
        monitor.generate_report()


if __name__ == '__main__':
    main()
