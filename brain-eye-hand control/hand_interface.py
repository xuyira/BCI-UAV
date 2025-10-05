#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hand Signal Interface Module
===========================

This module provides a standardized interface for hand gesture recognition.
It integrates with data glove hardware via serial communication and provides
real-time gesture recognition.

Supported Hand Gestures:
- FIST: Closed fist gesture
- FIVE: Open hand with all fingers extended
- GOOD: Thumbs up gesture
- ROCK: Rock and roll gesture (index and pinky extended)
- GUN: Gun gesture (thumb, index, middle extended)
- F_CK: Middle finger gesture

Author: [Your Name]
License: MIT
Version: 1.0.0
"""

import sys
import threading
import time
import serial
import re
from typing import Optional, Callable, Dict, Any
from pathlib import Path

# 使用本地模块
try:
    from gesture_recognizer import GestureRecognizer
except ImportError as e:
    print(f"警告：无法导入手部控制模块: {e}")
    GestureRecognizer = None


class HandSignalInterface:
    """手部信号接口类"""
    
    def __init__(self, port: str = 'COM6', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        
        # 组件初始化
        self.serial_conn = None
        self.gesture_recognizer = None
        
        # 运行状态
        self.is_running = False
        self.thread = None
        
        # 校准状态
        self.calibration_completed = False
        
        # 回调函数
        self.signal_callback: Optional[Callable[[str], None]] = None
        
        # 信号缓存
        self.last_signal = None
        self.current_data = {
            'timestamp': 0.0,
            'accel': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'gyro': {'x': 0.0, 'y': 0.0, 'z': 0.0},
            'angles': {'x': 0.0, 'y': 0.0},
            'fingers': {'thumb': 0.0, 'index': 0.0, 'middle': 0.0, 'ring': 0.0, 'pinky': 0.0},
        }
        
        # 静默初始化
    
    def set_signal_callback(self, callback: Callable[[str], None]):
        """设置信号回调函数"""
        self.signal_callback = callback
    
    def initialize(self) -> bool:
        """初始化手部控制组件"""
        if not GestureRecognizer:
            print("错误：手部控制模块未正确导入")
            return False
        
        try:
            # 初始化手势识别器
            self.gesture_recognizer = GestureRecognizer()
            
            # 初始化串口连接
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
            )
            
            # 静默初始化成功
            return True
            
        except Exception as e:
            print(f"错误：初始化手部控制组件失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动手部信号采集"""
        if not self.initialize():
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
        # 静默启动
        return True
    
    def stop(self):
        """停止手部信号采集"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        
        # 静默停止
    
    def _capture_loop(self):
        """信号采集主循环"""
        while self.is_running:
            try:
                if self.serial_conn and self.serial_conn.is_open:
                    line = self.serial_conn.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        time.sleep(0.01)
                        continue
                    
                    # 解析数据
                    data = self._parse_line(line)
                    if data:
                        self.current_data = data
                        
                        # 校准完成后开始识别
                        if self.calibration_completed:
                            self._process_hand_signal(data)
                
                time.sleep(0.01)
                
            except Exception as e:
                print(f"手部信号采集错误: {e}")
                time.sleep(0.1)
    
    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析串口数据"""
        try:
            # 校准数据
            if 'max_list:' in line or 'min_list:' in line:
                if not self.calibration_completed:
                    self.calibration_completed = True
                return None
            
            # 正则解析
            accel_match = re.search(r'ax:([\-\d.]+),\s*ay:([\-\d.]+),\s*az:([\-\d.]+)', line)
            gyro_match = re.search(r'gx:([\-\d.]+),\s*gy:([\-\d.]+),\s*gz:([\-\d.]+)', line)
            angle_match = re.search(r'GX:([\-\d.]+),\s*GY:([\-\d.]+)', line)
            fingers_match = re.search(r'fingers:([\-\d.]+)-([\-\d.]+)-([\-\d.]+)-([\-\d.]+)-([\-\d.]+)', line)
            
            if accel_match and gyro_match and angle_match:
                data = {
                    'timestamp': time.time(),
                    'accel': {
                        'x': float(accel_match.group(1)),
                        'y': float(accel_match.group(2)),
                        'z': float(accel_match.group(3)),
                    },
                    'gyro': {
                        'x': float(gyro_match.group(1)),
                        'y': float(gyro_match.group(2)),
                        'z': float(gyro_match.group(3)),
                    },
                    'angles': {
                        'x': float(angle_match.group(1)),
                        'y': float(angle_match.group(2)),
                    },
                    'fingers': {
                        'thumb': float(fingers_match.group(1)) if fingers_match else 0.0,
                        'index': float(fingers_match.group(2)) if fingers_match else 0.0,
                        'middle': float(fingers_match.group(3)) if fingers_match else 0.0,
                        'ring': float(fingers_match.group(4)) if fingers_match else 0.0,
                        'pinky': float(fingers_match.group(5)) if fingers_match else 0.0,
                    },
                }
                return data
            return None
        except Exception as e:
            print(f"解析错误: {e}")
            return None
    
    def _process_hand_signal(self, data: Dict[str, Any]):
        """处理手部信号"""
        if not self.gesture_recognizer:
            return
        
        # 手势识别
        gesture = self.gesture_recognizer.recognize(data)
        
        if gesture and gesture != self.last_signal:
            self.last_signal = gesture
            
            # 信号映射（将手部控制的输出映射到协同控制器需要的格式）
            mapped_signal = self._map_hand_signal(gesture)
            
            if mapped_signal:
                # 调用回调函数
                if self.signal_callback:
                    self.signal_callback(mapped_signal)
    
    def _map_hand_signal(self, signal: str) -> Optional[str]:
        """映射手部信号到协同控制器格式"""
        # 直接映射，因为手部控制已经输出了正确的格式
        signal_mapping = {
            "FIST": "FIST",
            "FIVE": "FIVE",
            "GOOD": "GOOD",
            "ROCK": "ROCK",
            "GUN": "GUN",
            "F_CK": "F_CK"
        }
        
        return signal_mapping.get(signal)
    
    def get_status(self) -> Dict[str, Any]:
        """获取接口状态"""
        return {
            "is_running": self.is_running,
            "port": self.port,
            "calibration_completed": self.calibration_completed,
            "last_signal": self.last_signal,
            "components_initialized": all([
                self.serial_conn is not None,
                self.gesture_recognizer is not None
            ]),
            "current_data": self.current_data
        }
    
    def force_calibration_complete(self):
        """强制完成校准（用于测试）"""
        self.calibration_completed = True
        print("强制完成手部控制校准")


def test_hand_interface():
    """测试手部信号接口"""
    print("=== 手部信号接口测试 ===")
    
    interface = HandSignalInterface(port='COM6')
    
    def signal_handler(signal: str):
        print(f"[信号处理器] 收到手部信号: {signal}")
    
    interface.set_signal_callback(signal_handler)
    
    try:
        if interface.start():
            print("手部信号接口启动成功，按Ctrl+C停止测试")
            print("等待校准完成...")
            
            # 等待校准完成
            while not interface.calibration_completed:
                time.sleep(0.1)
            
            print("校准完成，开始识别手势")
            
            while True:
                time.sleep(1)
                status = interface.get_status()
                print(f"状态: {status}")
        else:
            print("手部信号接口启动失败")
    except KeyboardInterrupt:
        print("\n用户中断测试")
    finally:
        interface.stop()


if __name__ == "__main__":
    test_hand_interface()
