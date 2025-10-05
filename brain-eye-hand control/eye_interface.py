#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eye Signal Interface Module
==========================

This module provides a standardized interface for eye tracking signals.
It integrates with the local eye tracking system and provides real-time
eye movement and blink detection.

Supported Eye Signals:
- UP/DOWN/LEFT/RIGHT: Eye movement directions
- LEFT_EYE_CLOSED/RIGHT_EYE_CLOSED: Individual eye blink detection
- CENTER: Neutral eye position

Author: [Your Name]
License: MIT
Version: 1.0.0
"""

import sys
import cv2
import threading
import time
from typing import Optional, Callable, Dict, Any
from pathlib import Path

# 使用本地模块
try:
    from video_input import VideoInput
    from gaze_model import GazeModel
    from controller import Controller
except ImportError as e:
    print(f"警告：无法导入眼部控制模块: {e}")
    VideoInput = None
    GazeModel = None
    Controller = None


class EyeSignalInterface:
    """眼部信号接口类"""
    
    def __init__(self, camera_index: int = 1, width: int = 640, height: int = 480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        
        # 组件初始化
        self.video_input = None
        self.gaze_model = None
        self.controller = None
        
        # 运行状态
        self.is_running = False
        self.thread = None
        
        # 回调函数
        self.signal_callback: Optional[Callable[[str], None]] = None
        
        # 信号缓存
        self.last_signal = None
        self.signal_buffer = []
        
        # 静默初始化
    
    def set_signal_callback(self, callback: Callable[[str], None]):
        """设置信号回调函数"""
        self.signal_callback = callback
    
    def initialize(self) -> bool:
        """初始化眼部控制组件"""
        if not all([VideoInput, GazeModel, Controller]):
            print("错误：眼部控制模块未正确导入")
            return False
        
        try:
            # 初始化视频输入
            self.video_input = VideoInput(
                self.camera_index, 
                width=self.width, 
                height=self.height, 
                api_preference="msmf"
            )
            
            if not self.video_input.is_opened():
                print(f"错误：无法打开摄像头 {self.camera_index}")
                return False
            
            # 初始化眼动模型
            self.gaze_model = GazeModel()
            
            # 初始化控制器
            self.controller = Controller(mode="auto")
            
            # 静默初始化成功
            return True
            
        except Exception as e:
            print(f"错误：初始化眼部控制组件失败: {e}")
            return False
    
    def start(self) -> bool:
        """启动眼部信号采集"""
        if not self.initialize():
            return False
        
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
        # 静默启动
        return True
    
    def stop(self):
        """停止眼部信号采集"""
        self.is_running = False
        
        if self.thread:
            self.thread.join(timeout=2)
        
        if self.video_input:
            self.video_input.release()
        
        # 静默停止
    
    def _capture_loop(self):
        """信号采集主循环"""
        while self.is_running:
            try:
                ok, frame = self.video_input.read()
                if not ok:
                    time.sleep(0.01)
                    continue
                
                # 180度旋转（与原始代码保持一致）
                frame = cv2.flip(frame, -1)
                
                # 眼动预测
                result = self.gaze_model.predict(frame)
                action = result.get("action")
                
                if action and action != "CENTER":
                    # 处理眼动信号
                    self._process_eye_signal(action)
                
                time.sleep(0.01)  # 控制帧率
                
            except Exception as e:
                print(f"眼部信号采集错误: {e}")
                time.sleep(0.1)
    
    def _process_eye_signal(self, signal: str):
        """处理眼部信号"""
        # 信号去重
        if signal == self.last_signal:
            return
        
        self.last_signal = signal
        
        # 信号映射（将眼部控制C的输出映射到协同控制器需要的格式）
        mapped_signal = self._map_eye_signal(signal)
        
        if mapped_signal:
            # 调用回调函数
            if self.signal_callback:
                self.signal_callback(mapped_signal)
    
    def _map_eye_signal(self, signal: str) -> Optional[str]:
        """映射眼部信号到协同控制器格式"""
        # 直接映射，因为眼部控制C已经输出了正确的格式
        signal_mapping = {
            "UP": "UP",
            "DOWN": "DOWN", 
            "LEFT": "LEFT",
            "RIGHT": "RIGHT",
            "LEFT_EYE_CLOSED": "LEFT_EYE_CLOSED",
            "RIGHT_EYE_CLOSED": "RIGHT_EYE_CLOSED"
        }
        
        return signal_mapping.get(signal)
    
    def get_status(self) -> Dict[str, Any]:
        """获取接口状态"""
        return {
            "is_running": self.is_running,
            "camera_index": self.camera_index,
            "last_signal": self.last_signal,
            "components_initialized": all([
                self.video_input is not None,
                self.gaze_model is not None,
                self.controller is not None
            ])
        }


def test_eye_interface():
    """测试眼部信号接口"""
    print("=== 眼部信号接口测试 ===")
    
    interface = EyeSignalInterface(camera_index=1)
    
    def signal_handler(signal: str):
        print(f"[信号处理器] 收到眼部信号: {signal}")
    
    interface.set_signal_callback(signal_handler)
    
    try:
        if interface.start():
            print("眼部信号接口启动成功，按Ctrl+C停止测试")
            while True:
                time.sleep(1)
                status = interface.get_status()
                print(f"状态: {status}")
        else:
            print("眼部信号接口启动失败")
    except KeyboardInterrupt:
        print("\n用户中断测试")
    finally:
        interface.stop()


if __name__ == "__main__":
    test_eye_interface()
