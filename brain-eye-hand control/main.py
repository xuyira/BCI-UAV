#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hand-Eye Coordination Controller
================================

A real-time hand-eye coordination control system that integrates eye tracking 
and hand gesture recognition for multi-stage control operations.

Features:
- Three-stage control logic (target selection → action control → output)
- Eye tracking with blink detection
- Hand gesture recognition via data glove
- Automatic state transitions and signal quality control
- Support for multiple control sequences including special 4-signal sequence

Author: [Your Name]
License: MIT
Version: 1.0.0
"""

import argparse
import time
import sys
from typing import Optional

from coordinator import HandEyeCoordinator, ControlStage
from eye_interface import EyeSignalInterface
from hand_interface import HandSignalInterface


class HandEyeControlSystem:
    """手眼协同控制系统主类"""
    
    def __init__(self, camera_index: int = 1, hand_port: str = 'COM6'):
        self.camera_index = camera_index
        self.hand_port = hand_port
        
        # 初始化组件
        self.coordinator = HandEyeCoordinator()
        self.eye_interface = EyeSignalInterface(camera_index=camera_index)
        self.hand_interface = HandSignalInterface(port=hand_port)
        
        # 运行状态
        self.is_running = False
        
        # 输出统计
        self.output_count = 0
        self.start_time = None
        
        # 静默初始化
    
    def start(self) -> bool:
        """启动系统"""
        print("=== 启动手眼协同控制系统 ===")
        
        # 设置回调函数
        self.coordinator.set_output_callback(self._handle_output)
        self.eye_interface.set_signal_callback(self._handle_eye_signal)
        self.hand_interface.set_signal_callback(self._handle_hand_signal)
        
        # 启动各个接口
        if not self.eye_interface.start():
            print("错误：眼部信号接口启动失败")
            return False
        
        if not self.hand_interface.start():
            print("错误：手部信号接口启动失败")
            return False
        
        # 等待手部控制校准完成
        while not self.hand_interface.get_status()['calibration_completed']:
            time.sleep(0.1)
        
        print("进入阶段1")
        
        # 设置运行状态
        self.is_running = True
        self.start_time = time.time()
        
        return True
    
    def stop(self):
        """停止系统"""
        self.is_running = False
        
        # 停止各个接口
        self.eye_interface.stop()
        self.hand_interface.stop()
    
    def _handle_eye_signal(self, signal: str):
        """处理眼部信号"""
        processed = self.coordinator.process_eye_signal(signal)
        if processed:
            # 只在阶段1输出眼部信号
            if self.coordinator.current_stage.value == 1:
                print(signal)
    
    def _handle_hand_signal(self, signal: str):
        """处理手部信号"""
        processed = self.coordinator.process_hand_signal(signal)
        if processed:
            # 只在阶段2输出手部信号
            if self.coordinator.current_stage.value == 2:
                print(signal)
    
    def _handle_output(self, output: str):
        """处理最终输出（已由协同控制器处理）"""
        self.output_count += 1
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        return {
            "is_running": self.is_running,
            "coordinator_state": self.coordinator.get_current_state(),
            "eye_status": self.eye_interface.get_status(),
            "hand_status": self.hand_interface.get_status(),
            "output_count": self.output_count,
            "runtime": time.time() - self.start_time if self.start_time else 0
        }


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="手眼协同控制器")
    parser.add_argument("--camera", type=int, default=1, help="摄像头索引 (默认: 1)")
    parser.add_argument("--hand-port", type=str, default="COM6", help="手部控制串口 (默认: COM6)")
    parser.add_argument("--test", action="store_true", help="运行测试模式")
    return parser.parse_args()


def test_mode():
    """测试模式"""
    print("=== 测试模式 ===")
    
    # 测试协同控制器
    print("\n1. 测试协同控制器...")
    from coordinator import test_coordinator
    test_coordinator()
    
    # 测试眼部接口（需要摄像头）
    print("\n2. 测试眼部接口...")
    try:
        from eye_interface import test_eye_interface
        test_eye_interface()
    except Exception as e:
        print(f"眼部接口测试失败: {e}")
    
    # 测试手部接口（需要串口连接）
    print("\n3. 测试手部接口...")
    try:
        from hand_interface import test_hand_interface
        test_hand_interface()
    except Exception as e:
        print(f"手部接口测试失败: {e}")


def main():
    """主函数"""
    args = parse_args()
    
    if args.test:
        test_mode()
        return
    
    # 创建系统
    system = HandEyeControlSystem(
        camera_index=args.camera,
        hand_port=args.hand_port
    )
    
    try:
        # 启动系统
        if system.start():
            # 主循环
            while True:
                time.sleep(1)
        else:
            print("系统启动失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"系统错误: {e}")
        return 1
    finally:
        system.stop()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
