#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hand-Eye Coordination Controller Core Module
===========================================

This module implements the core coordination logic for the hand-eye control system.
It manages three-stage control flow and signal quality control.

Control Stages:
1. Target Selection: Eye signals select control targets (1-5)
2. Action Control: Hand signals specify control actions
3. Output Generation: Final control command generation and auto-return to stage 1

Supported Control Sequences:
- LEFT + LEFT_EYE_CLOSED = Target 1
- RIGHT + RIGHT_EYE_CLOSED = Target 2
- LEFT + RIGHT_EYE_CLOSED = Target 3
- RIGHT + LEFT_EYE_CLOSED = Target 4
- LEFT + RIGHT + LEFT_EYE_CLOSED + RIGHT_EYE_CLOSED = Target 5 (Special)

Author: [Your Name]
License: MIT
Version: 1.0.0
"""

import time
import threading
from typing import Optional, Dict, Any
from enum import Enum
from collections import deque


class ControlStage(Enum):
    """控制阶段枚举"""
    STAGE1_TARGET_SELECTION = 1  # 阶段1：目标选定
    STAGE2_ACTION_CONTROL = 2    # 阶段2：动作控制
    STAGE3_OUTPUT = 3            # 阶段3：输出控制


class HandEyeCoordinator:
    """手眼协同控制器主类"""
    
    def __init__(self):
        self.current_stage = ControlStage.STAGE1_TARGET_SELECTION
        self.selected_target = None  # 选定的目标编号 (1-4)
        self.last_hand_action = None  # 最后的手部动作
        
        # 信号质量控制
        self.last_eye_signal = None
        self.eye_signal_buffer = deque(maxlen=3)  # 眼部信号缓冲，用于去重
        self.hand_signal_received = False  # 是否已接收手部信号
        
        # 目标映射规则
        self.target_mapping = {
            ("LEFT", "LEFT_EYE_CLOSED"): 1,
            ("RIGHT", "RIGHT_EYE_CLOSED"): 2,
            ("LEFT", "RIGHT_EYE_CLOSED"): 3,
            ("RIGHT", "LEFT_EYE_CLOSED"): 4,
        }
        
        # 特殊控制序列：LEFT + RIGHT + LEFT_EYE_CLOSED + RIGHT_EYE_CLOSED = 5
        self.special_sequence = ["LEFT", "RIGHT", "LEFT_EYE_CLOSED", "RIGHT_EYE_CLOSED"]
        self.special_sequence_buffer = deque(maxlen=4)  # 存储特殊序列的缓冲区
        
        # 输出回调函数
        self.output_callback = None
        
        # 线程锁
        self.lock = threading.Lock()
        
        print("手眼协同控制器初始化完成")
    
    def set_output_callback(self, callback):
        """设置输出回调函数"""
        self.output_callback = callback
    
    def process_eye_signal(self, eye_action: str) -> bool:
        """
        处理眼部信号
        返回True表示信号被处理，False表示信号被忽略
        """
        with self.lock:
            # 信号质量控制：不输出DOWN
            if eye_action == "DOWN":
                return False
            
            # 信号质量控制：连续相同的信号只输出一个
            if eye_action == self.last_eye_signal:
                return False
            
            self.last_eye_signal = eye_action
            
            # 根据当前阶段处理信号
            if self.current_stage == ControlStage.STAGE1_TARGET_SELECTION:
                return self._handle_stage1_eye_signal(eye_action)
            else:
                # 阶段2和3中，眼部信号用于解除选定
                if eye_action == "UP":
                    self._reset_to_stage1()
                    return True
                return False
    
    def process_hand_signal(self, hand_action: str) -> bool:
        """
        处理手部信号
        返回True表示信号被处理，False表示信号被忽略
        """
        with self.lock:
            # 信号质量控制：只有进入阶段2才输出手部信号
            if self.current_stage != ControlStage.STAGE2_ACTION_CONTROL:
                return False
            
            # 信号质量控制：产生一个手部信号后直接进入阶段3
            self.last_hand_action = hand_action
            self.hand_signal_received = True
            self.current_stage = ControlStage.STAGE3_OUTPUT
            
            print("进入阶段3")
            print(f"最终输出为：{self.selected_target} {hand_action}")
            
        # 对外回调：让外部（如 HTTP 客户端）接收最终输出
        if self.output_callback:
            try:
                self.output_callback(f"{self.selected_target} {hand_action}")
            except Exception:
                pass
        
            # 自动回到阶段1
            self._reset_to_stage1()
            
            return True
    
    def _handle_stage1_eye_signal(self, eye_action: str) -> bool:
        """处理阶段1的眼部信号"""
        if eye_action == "UP":
            # 解除选定，回到阶段1初始
            self._reset_to_stage1()
            return True
        
        # 添加信号到特殊序列缓冲区
        self.special_sequence_buffer.append(eye_action)
        
        # 检查特殊序列：LEFT + RIGHT + LEFT_EYE_CLOSED + RIGHT_EYE_CLOSED = 5
        if len(self.special_sequence_buffer) == 4:
            if list(self.special_sequence_buffer) == self.special_sequence:
                self.selected_target = 5
                self.current_stage = ControlStage.STAGE2_ACTION_CONTROL
                self.hand_signal_received = False
                print("进入阶段2")
                return True
        
        # 检查是否为目标选定信号（原有的两信号组合）
        for (direction, blink), target_num in self.target_mapping.items():
            if eye_action == direction:
                # 需要等待眨眼信号来确认目标
                self.eye_signal_buffer.append(eye_action)
                return True
            elif eye_action == blink:
                # 检查是否有对应的方向信号
                if direction in self.eye_signal_buffer:
                    self.selected_target = target_num
                    self.current_stage = ControlStage.STAGE2_ACTION_CONTROL
                    self.hand_signal_received = False
                    print("进入阶段2")
                    return True
        
        # 如果信号不构成控制序列，则不输出
        return False
    
    def _reset_to_stage1(self):
        """重置到阶段1"""
        self.current_stage = ControlStage.STAGE1_TARGET_SELECTION
        self.selected_target = None
        self.last_hand_action = None
        self.hand_signal_received = False
        self.eye_signal_buffer.clear()
        self.special_sequence_buffer.clear()
        print("进入阶段1")
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态信息"""
        with self.lock:
            return {
                "stage": self.current_stage.value,
                "selected_target": self.selected_target,
                "last_hand_action": self.last_hand_action,
                "last_eye_signal": self.last_eye_signal,
                "hand_signal_received": self.hand_signal_received
            }
    
    def generate_output(self) -> Optional[str]:
        """
        生成最终输出
        返回格式："数字 手部动作"，如"1 FIST"，"2 GOOD"等
        """
        with self.lock:
            if (self.current_stage == ControlStage.STAGE3_OUTPUT and 
                self.selected_target is not None and 
                self.last_hand_action is not None):
                
                output = f"{self.selected_target} {self.last_hand_action}"
                print(f"[输出] {output}")
                
                # 输出后回到阶段1
                self._reset_to_stage1()
                
                # 调用输出回调
                if self.output_callback:
                    self.output_callback(output)
                
                return output
        
        return None
    
    def force_output(self) -> Optional[str]:
        """强制输出当前状态（用于测试）"""
        return self.generate_output()
    
    def get_stage_description(self) -> str:
        """获取当前阶段的描述"""
        stage_descriptions = {
            ControlStage.STAGE1_TARGET_SELECTION: "阶段1：眼部信号选定目标",
            ControlStage.STAGE2_ACTION_CONTROL: "阶段2：手部信号控制动作",
            ControlStage.STAGE3_OUTPUT: "阶段3：输出最终控制"
        }
        return stage_descriptions.get(self.current_stage, "未知阶段")


def test_coordinator():
    """测试协同控制器"""
    print("=== 手眼协同控制器测试 ===")
    
    coordinator = HandEyeCoordinator()
    
    def output_handler(output: str):
        print(f"[输出处理器] 收到输出: {output}")
    
    coordinator.set_output_callback(output_handler)
    
    # 测试序列1：选定目标1
    print("\n--- 测试序列1：选定目标1 ---")
    coordinator.process_eye_signal("LEFT")  # 方向信号
    coordinator.process_eye_signal("LEFT_EYE_CLOSED")  # 眨眼信号
    coordinator.process_hand_signal("FIST")  # 手部动作
    coordinator.generate_output()  # 生成输出
    
    # 测试序列2：选定目标2
    print("\n--- 测试序列2：选定目标2 ---")
    coordinator.process_eye_signal("RIGHT")  # 方向信号
    coordinator.process_eye_signal("RIGHT_EYE_CLOSED")  # 眨眼信号
    coordinator.process_hand_signal("GOOD")  # 手部动作
    coordinator.generate_output()  # 生成输出
    
    # 测试序列3：信号质量控制
    print("\n--- 测试序列3：信号质量控制 ---")
    coordinator.process_eye_signal("DOWN")  # 应该被忽略
    coordinator.process_eye_signal("LEFT")  # 重复信号，应该被忽略
    coordinator.process_eye_signal("LEFT")  # 重复信号，应该被忽略
    coordinator.process_eye_signal("LEFT_EYE_CLOSED")  # 眨眼信号
    coordinator.process_hand_signal("FIVE")  # 手部动作
    coordinator.generate_output()  # 生成输出
    
    # 测试序列4：解除选定
    print("\n--- 测试序列4：解除选定 ---")
    coordinator.process_eye_signal("LEFT")
    coordinator.process_eye_signal("LEFT_EYE_CLOSED")
    coordinator.process_eye_signal("UP")  # 解除选定
    print(f"当前状态: {coordinator.get_current_state()}")


if __name__ == "__main__":
    test_coordinator()
