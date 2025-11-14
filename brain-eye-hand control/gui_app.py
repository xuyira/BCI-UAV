#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞行员作业能力测试工具箱 - 图形界面
==================================

该模块提供手眼脑协同控制端的图形化界面，用于启动和停止
`main.py` 中定义的手眼协同控制系统，同时实时展示控制端的输出。
"""

import os
import queue
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from typing import Callable, List, Optional
from tkinter import messagebox
from tkinter import scrolledtext


class ControlPanel(tk.Frame):
    """手眼脑协同控制端面板"""

    def __init__(self, master: tk.Misc, **kwargs):
        super().__init__(master, **kwargs)
        self.process: Optional[subprocess.Popen] = None
        self.output_queue: queue.Queue = queue.Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self.output_listeners: List[Callable[[str], None]] = []

        # 被试界面状态
        self.stage1_target_var = tk.StringVar(value="阶段一（无人机）：--")
        self.stage2_action_var = tk.StringVar(value="阶段二（动作）：--")
        self.final_output_var = tk.StringVar(value="最终输出：--")
        self.current_stage = 1  # 1, 2, 3
        self.selected_target: Optional[int] = None
        self.clear_after_id: Optional[str] = None
        
        # 阶段1信号缓冲区，用于识别目标编号
        self.stage1_signals = []
        self.target_mapping = {
            ("LEFT", "LEFT_EYE_CLOSED"): 1,
            ("RIGHT", "RIGHT_EYE_CLOSED"): 2,
            ("LEFT", "RIGHT_EYE_CLOSED"): 3,
            ("RIGHT", "LEFT_EYE_CLOSED"): 4,
        }
        self.special_sequence = ["LEFT", "RIGHT", "LEFT_EYE_CLOSED", "RIGHT_EYE_CLOSED"]
        
        # 显示模式：0=只看被试, 1=只看主试, 2=都看
        self.display_mode = 2

        self._build_ui()
        self._schedule_output_poll()

    def register_output_listener(self, listener: Callable[[str], None]):
        if listener not in self.output_listeners:
            self.output_listeners.append(listener)

    def unregister_output_listener(self, listener: Callable[[str], None]):
        if listener in self.output_listeners:
            self.output_listeners.remove(listener)

    def _build_ui(self):
        title = tk.Label(self, text="手眼脑协同控制端", font=("Microsoft YaHei", 16, "bold"))
        title.pack(anchor="w", pady=(0, 16))

        button_frame = tk.Frame(self)
        button_frame.pack(fill="x", pady=(0, 12))

        self.start_button = tk.Button(
            button_frame,
            text="开始",
            width=10,
            command=self.start_control,
            bg="#4CAF50",
            fg="#FFFFFF",
            activebackground="#45A049",
        )
        self.start_button.pack(side="left")

        self.stop_button = tk.Button(
            button_frame,
            text="结束",
            width=10,
            command=self.stop_control,
            state=tk.DISABLED,
            bg="#F44336",
            fg="#FFFFFF",
            activebackground="#D32F2F",
        )
        self.stop_button.pack(side="left", padx=(12, 0))

        # 显示模式切换按钮（3个独立按钮）
        mode_frame = tk.Frame(button_frame)
        mode_frame.pack(side="right")
        
        self.mode_buttons = []
        mode_texts = ["主试", "被试", "主+被"]
        for i, text in enumerate(mode_texts):
            btn = tk.Button(
                mode_frame,
                text=text,
                width=8,
                command=lambda m=i: self.set_display_mode(m),
            )
            btn.pack(side="left", padx=(0, 4))
            self.mode_buttons.append(btn)
        
        # 初始高亮"主+被"按钮
        self._update_mode_buttons()

        # 被试界面显示区域
        self.subject_frame = tk.LabelFrame(self, text="被试界面")
        
        stage1_lbl = tk.Label(
            self.subject_frame,
            textvariable=self.stage1_target_var,
            font=("Microsoft YaHei", 14, "bold"),
            fg="#4CAF50",
            anchor="w",
        )
        stage1_lbl.pack(fill="x", padx=12, pady=(8, 4))

        stage2_lbl = tk.Label(
            self.subject_frame,
            textvariable=self.stage2_action_var,
            font=("Microsoft YaHei", 14, "bold"),
            fg="#FF9800",
            anchor="w",
        )
        stage2_lbl.pack(fill="x", padx=12, pady=(4, 4))

        final_lbl = tk.Label(
            self.subject_frame,
            textvariable=self.final_output_var,
            font=("Microsoft YaHei", 14, "bold"),
            fg="#2196F3",
            anchor="w",
        )
        final_lbl.pack(fill="x", padx=12, pady=(4, 8))

        # 主试界面（终端输出）
        self.examiner_frame = tk.Frame(self)
        
        self.output_text = scrolledtext.ScrolledText(
            self.examiner_frame,
            wrap=tk.WORD,
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="#FFFFFF",
            state=tk.DISABLED,
        )
        self.output_text.pack(fill="both", expand=True)

        # 初始显示模式
        self._update_display_mode()

    def set_display_mode(self, mode: int):
        """设置显示模式：0=只看主试, 1=只看被试, 2=都看"""
        self.display_mode = mode
        self._update_display_mode()
        self._update_mode_buttons()

    def _update_mode_buttons(self):
        """更新按钮高亮状态"""
        for i, btn in enumerate(self.mode_buttons):
            if i == self.display_mode:
                # 高亮当前选中的按钮
                btn.config(bg="#2196F3", fg="#FFFFFF", activebackground="#1976D2")
            else:
                # 普通按钮样式
                btn.config(bg="#E0E0E0", fg="#000000", activebackground="#BDBDBD")

    def _update_display_mode(self):
        """更新显示模式"""
        # 先隐藏所有
        self.subject_frame.pack_forget()
        self.examiner_frame.pack_forget()
        
        # 根据模式显示
        if self.display_mode == 0:  # 只看主试
            self.subject_frame.pack_forget()
            self.examiner_frame.pack(fill="both", expand=True)
        elif self.display_mode == 1:  # 只看被试
            self.subject_frame.pack(fill="both", expand=True, pady=(0, 12))
            self.examiner_frame.pack_forget()
        else:  # 都看
            self.subject_frame.pack(fill="x", pady=(0, 12))
            self.examiner_frame.pack(fill="both", expand=True)

    def start_control(self):
        if self.process and self.process.poll() is None:
            messagebox.showwarning("提示", "系统已在运行中。")
            return

        python_executable = sys.executable
        script_path = os.path.join(os.path.dirname(__file__), "main.py")

        if not os.path.exists(script_path):
            messagebox.showerror("错误", f"未找到主程序：{script_path}")
            return

        try:
            self._append_output(">>> 启动手眼协同控制系统...\n")
            # 清空被试界面
            self._clear_subject_ui()
            self.current_stage = 1
            self.process = subprocess.Popen(
                [python_executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=os.path.dirname(script_path),
            )
        except Exception as exc:
            messagebox.showerror("错误", f"无法启动主程序：\n{exc}")
            self.process = None
            return

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self.reader_thread.start()

    def stop_control(self):
        if not self.process:
            return

        if self.process.poll() is None:
            self._append_output(">>> 正在结束手眼协同控制系统...\n")
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as exc:
                self._append_output(f">>> 结束进程时出现异常：{exc}\n")

        self._cleanup_process()

    def _read_output(self):
        assert self.process is not None and self.process.stdout is not None

        for line in self.process.stdout:
            self.output_queue.put(line)

        return_code = self.process.wait()
        self.output_queue.put(f">>> 主程序退出，返回码：{return_code}\n")
        self.output_queue.put(None)

    def _schedule_output_poll(self):
        self.after(100, self._process_output_queue)

    def _process_output_queue(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                if line is None:
                    self._cleanup_process()
                    break
                self._append_output(line)
        except queue.Empty:
            pass
        finally:
            self._schedule_output_poll()

    def _append_output(self, text: str):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)
        stripped = text.strip()
        if stripped:
            # 解析输出并更新被试界面
            self._parse_and_update_subject_ui(stripped)
            for listener in list(self.output_listeners):
                listener(stripped)

    def _parse_and_update_subject_ui(self, line: str):
        """解析输出文本并更新被试界面"""
        # 取消之前的清空定时器
        if self.clear_after_id:
            self.after_cancel(self.clear_after_id)
            self.clear_after_id = None

        # 检测阶段变化
        if "进入阶段1" in line:
            self.current_stage = 1
            self.selected_target = None
            self.stage1_signals = []  # 清空信号缓冲区
            # 2秒后清空显示
            self.clear_after_id = self.after(2000, self._clear_subject_ui)
        elif "进入阶段2" in line:
            self.current_stage = 2
            # 阶段1保持不变，清空阶段2和最终输出
            self.stage2_action_var.set("阶段二（动作）：--")
            self.final_output_var.set("最终输出：--")
            # 根据信号序列推断目标编号（如果还没有显示）
            if self.stage1_target_var.get() == "阶段一（无人机）：--" and self.stage1_signals:
                target = self._infer_target_from_signals()
                if target:
                    self.stage1_target_var.set(f"阶段一（无人机）：{target}")
                    self.selected_target = target
        elif "进入阶段3" in line:
            self.current_stage = 3
        elif "最终输出为：" in line:
            # 解析最终输出：格式为 "最终输出为：<target> <gesture>"
            try:
                parts = line.split("最终输出为：")
                if len(parts) == 2:
                    output_parts = parts[1].strip().split()
                    if len(output_parts) >= 2:
                        target = int(output_parts[0])
                        gesture = output_parts[1]
                        self.selected_target = target
                        # 更新阶段1显示（如果之前没有显示）
                        if "阶段一（无人机）：--" in self.stage1_target_var.get():
                            self.stage1_target_var.set(f"阶段一（无人机）：{target}")
                        # 更新阶段2显示（如果之前没有显示）
                        if "阶段二（动作）：--" in self.stage2_action_var.get():
                            self.stage2_action_var.set(f"阶段二（动作）：{gesture}")
                        # 更新最终输出
                        self.final_output_var.set(f"最终输出：{target} {gesture}")
            except Exception:
                pass
        elif self.current_stage == 1:
            # 阶段1：收集信号并尝试识别目标编号
            # 有效的眼部信号
            valid_signals = ["LEFT", "RIGHT", "LEFT_EYE_CLOSED", "RIGHT_EYE_CLOSED", "UP", "DOWN"]
            if line in valid_signals and line != "DOWN":  # 忽略DOWN信号
                # 添加到信号缓冲区（保持最近4个信号）
                self.stage1_signals.append(line)
                if len(self.stage1_signals) > 4:
                    self.stage1_signals = self.stage1_signals[-4:]
                
                # 尝试识别目标编号
                target = self._infer_target_from_signals()
                if target:
                    self.stage1_target_var.set(f"阶段一（无人机）：{target}")
                    self.selected_target = target
        elif self.current_stage == 2:
            # 阶段2：显示手部动作
            # 手部动作信号：FIST, FIVE, GOOD, ROCK, GUN, F_CK
            gestures = ["FIST", "FIVE", "GOOD", "ROCK", "GUN", "F_CK"]
            if line in gestures:
                self.stage2_action_var.set(f"阶段二（动作）：{line}")
    
    def _infer_target_from_signals(self) -> Optional[int]:
        """根据信号序列推断目标编号"""
        if not self.stage1_signals:
            return None
        
        # 检查特殊序列：LEFT + RIGHT + LEFT_EYE_CLOSED + RIGHT_EYE_CLOSED = 5
        if len(self.stage1_signals) >= 4:
            last_four = self.stage1_signals[-4:]
            if last_four == self.special_sequence:
                return 5
        
        # 检查普通映射：需要方向信号+眨眼信号
        # 查找最近的方向信号和眨眼信号
        directions = ["LEFT", "RIGHT"]
        blinks = ["LEFT_EYE_CLOSED", "RIGHT_EYE_CLOSED"]
        
        last_direction = None
        last_blink = None
        
        for signal in reversed(self.stage1_signals):
            if signal in directions and last_direction is None:
                last_direction = signal
            elif signal in blinks and last_blink is None:
                last_blink = signal
            if last_direction and last_blink:
                break
        
        if last_direction and last_blink:
            key = (last_direction, last_blink)
            if key in self.target_mapping:
                return self.target_mapping[key]
        
        return None

    def _clear_subject_ui(self):
        """清空被试界面显示"""
        self.stage1_target_var.set("阶段一（无人机）：--")
        self.stage2_action_var.set("阶段二（动作）：--")
        self.final_output_var.set("最终输出：--")
        self.selected_target = None
        self.stage1_signals = []
        self.clear_after_id = None

    def _cleanup_process(self):
        if self.process and self.process.stdout:
            try:
                self.process.stdout.close()
            except Exception:
                pass

        # 取消清空定时器
        if self.clear_after_id:
            self.after_cancel(self.clear_after_id)
            self.clear_after_id = None

        self.process = None
        self.reader_thread = None
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        # 清空被试界面
        self._clear_subject_ui()


class CognitiveTestPanel(tk.Frame):
    """作业能力测试端"""

    GESTURES = ["FIST", "FIVE", "GOOD", "ROCK", "GUN", "F_CK"]

    def __init__(self, master: tk.Misc, control_panel: ControlPanel, **kwargs):
        super().__init__(master, **kwargs)
        self.control_panel = control_panel

        self.reaction_score_var = tk.StringVar(value="反应力得分：--")
        self.attention_score_var = tk.StringVar(value="注意力得分：--")
        self.memory_score_var = tk.StringVar(value="记忆力得分：--")
        self.planning_score_var = tk.StringVar(value="规划力得分：--")
        self.status_var = tk.StringVar(value="正在测试：--")
        self.prompt_var = tk.StringVar(value="")

        # 显示模式：0=只看被试, 1=只看主试, 2=都看
        self.display_mode = 2
        
        # 记忆力测试相关
        self.memory_active = False
        self.memory_scores: List[float] = []
        self.memory_prompt_after_id: Optional[str] = None
        self.memory_hide_after_id: Optional[str] = None
        self.memory_timeout_after_id: Optional[str] = None
        self.current_trial: Optional[dict] = None
        self.memory_start_time: Optional[datetime] = None
        self.memory_trial_count = 0
        self.memory_log_lines: List[str] = []

        self._build_ui()
        self.control_panel.register_output_listener(self._handle_control_output)

    def _build_ui(self):
        title = tk.Label(self, text="作业能力测试端", font=("Microsoft YaHei", 16, "bold"))
        title.pack(anchor="w", pady=(0, 16))

        btn_grid = tk.Frame(self)
        btn_grid.pack(fill="x", pady=(0, 16))

        # 反应力
        reaction_btn = tk.Button(
            btn_grid,
            text="反应力测试",
            state=tk.DISABLED,
            width=12,
        )
        reaction_btn.grid(row=0, column=0, padx=(0, 12), pady=(0, 8), sticky="w")
        reaction_score_lbl = tk.Label(btn_grid, textvariable=self.reaction_score_var, anchor="w")
        reaction_score_lbl.grid(row=0, column=1, sticky="w")

        # 注意力
        attention_btn = tk.Button(
            btn_grid,
            text="注意力测试",
            state=tk.DISABLED,
            width=12,
        )
        attention_btn.grid(row=1, column=0, padx=(0, 12), pady=(0, 8), sticky="w")
        attention_score_lbl = tk.Label(btn_grid, textvariable=self.attention_score_var, anchor="w")
        attention_score_lbl.grid(row=1, column=1, sticky="w")

        # 记忆力
        self.memory_button = tk.Button(
            btn_grid,
            text="记忆力测试",
            width=12,
            command=self.toggle_memory_test,
        )
        self.memory_button.grid(row=2, column=0, padx=(0, 12), pady=(0, 8), sticky="w")
        memory_score_lbl = tk.Label(btn_grid, textvariable=self.memory_score_var, anchor="w")
        memory_score_lbl.grid(row=2, column=1, sticky="w")

        # 规划力
        planning_btn = tk.Button(
            btn_grid,
            text="规划力测试",
            state=tk.DISABLED,
            width=12,
        )
        planning_btn.grid(row=3, column=0, padx=(0, 12), sticky="w")
        planning_score_lbl = tk.Label(btn_grid, textvariable=self.planning_score_var, anchor="w")
        planning_score_lbl.grid(row=3, column=1, sticky="w")

        display_frame = tk.LabelFrame(self, text="测试显示窗口")
        display_frame.pack(fill="both", expand=True)

        # 切换按钮（3个独立按钮）
        switch_frame = tk.Frame(display_frame)
        switch_frame.pack(fill="x", padx=12, pady=(8, 8))
        
        self.mode_buttons = []
        mode_texts = ["主试", "被试", "主+被"]
        for i, text in enumerate(mode_texts):
            btn = tk.Button(
                switch_frame,
                text=text,
                width=8,
                command=lambda m=i: self.set_display_mode(m),
            )
            btn.pack(side="left", padx=(0, 4))
            self.mode_buttons.append(btn)
        
        # 初始高亮"主+被"按钮
        self._update_mode_buttons()

        # 被试界面内容
        self.subject_frame = tk.Frame(display_frame)
        
        status_lbl = tk.Label(
            self.subject_frame,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 13, "bold"),
        )
        status_lbl.pack(anchor="w", padx=12, pady=(0, 4))

        self.prompt_lbl = tk.Label(
            self.subject_frame,
            textvariable=self.prompt_var,
            font=("Microsoft YaHei", 16, "bold"),
            fg="#FF9800",
            wraplength=400,
        )
        self.prompt_lbl.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # 主试界面内容
        self.examiner_frame = tk.Frame(display_frame)
        
        self.examiner_text = scrolledtext.ScrolledText(
            self.examiner_frame,
            wrap=tk.WORD,
            bg="#1E1E1E",
            fg="#D4D4D4",
            insertbackground="#FFFFFF",
            state=tk.DISABLED,
            font=("Consolas", 10),
        )
        self.examiner_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # 初始显示被试界面
        self._update_display_mode()
        
        # 绑定窗口大小改变事件，动态更新 wraplength
        self.bind("<Configure>", self._on_window_configure)
    
    def _on_window_configure(self, event):
        """窗口大小改变时更新 wraplength"""
        if event.widget == self:
            self.after_idle(self._update_prompt_wraplength)

    def set_display_mode(self, mode: int):
        """设置显示模式：0=只看主试, 1=只看被试, 2=都看"""
        self.display_mode = mode
        self._update_display_mode()
        self._update_mode_buttons()

    def _update_mode_buttons(self):
        """更新按钮高亮状态"""
        for i, btn in enumerate(self.mode_buttons):
            if i == self.display_mode:
                # 高亮当前选中的按钮
                btn.config(bg="#2196F3", fg="#FFFFFF", activebackground="#1976D2")
            else:
                # 普通按钮样式
                btn.config(bg="#E0E0E0", fg="#000000", activebackground="#BDBDBD")

    def _update_display_mode(self):
        """更新显示模式"""
        # 先隐藏所有
        self.subject_frame.pack_forget()
        self.examiner_frame.pack_forget()
        
        # 根据模式显示
        if self.display_mode == 0:  # 只看主试
            self.subject_frame.pack_forget()
            self.examiner_frame.pack(fill="both", expand=True)
        elif self.display_mode == 1:  # 只看被试
            self.subject_frame.pack(fill="both", expand=True)
            self.examiner_frame.pack_forget()
            # 更新 wraplength 以适应实际宽度
            self.after_idle(self._update_prompt_wraplength)
        else:  # 都看
            self.subject_frame.pack(fill="both", expand=True)
            self.examiner_frame.pack(fill="both", expand=True)
            # 更新 wraplength 以适应实际宽度
            self.after_idle(self._update_prompt_wraplength)
    
    def _update_prompt_wraplength(self):
        """动态更新提示文字的换行长度"""
        if self.display_mode != 0 and self.subject_frame.winfo_ismapped():  # 不是只看主试模式
            try:
                frame_width = self.subject_frame.winfo_width()
                if frame_width > 1:  # 确保已经渲染
                    # 减去左右padding (12*2) 和一点边距
                    new_wraplength = max(200, frame_width - 50)
                    self.prompt_lbl.config(wraplength=new_wraplength)
            except Exception:
                pass

    def _append_examiner_log(self, text: str):
        """在主试界面添加日志"""
        self.examiner_text.config(state=tk.NORMAL)
        self.examiner_text.insert(tk.END, text + "\n")
        self.examiner_text.see(tk.END)
        self.examiner_text.config(state=tk.DISABLED)
        # 同时记录到日志列表
        self.memory_log_lines.append(text)

    def toggle_memory_test(self):
        if self.memory_active:
            self._stop_memory_test()
        else:
            self._start_memory_test()

    def _start_memory_test(self):
        self.memory_active = True
        self.status_var.set("正在测试：记忆力")
        self.memory_button.config(text="停止记忆力测试")
        self.memory_scores = []
        self.memory_trial_count = 0
        self.memory_log_lines = []
        self._clear_prompt()
        
        # 记录开始时间
        self.memory_start_time = datetime.now()
        start_time_str = self.memory_start_time.strftime("%Y年%m月%d日%H时%M分%S秒")
        log_text = f"开始记忆力测试，当前时间：{start_time_str}"
        self._append_examiner_log(log_text)
        
        self._schedule_next_memory_round(initial=True)

    def _stop_memory_test(self):
        # 保存日志文件
        if self.memory_start_time and self.memory_log_lines:
            try:
                start_time_str = self.memory_start_time.strftime("%Y年%m月%d日%H时%M分%S秒")
                filename = f"记忆力测试-{start_time_str}.txt"
                # 创建保存目录
                save_dir = os.path.join(os.path.dirname(__file__), "pilot_results", "记忆力测试")
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write("\n".join(self.memory_log_lines))
                self._append_examiner_log(f"\n测试日志已保存至：{os.path.join('pilot_results', '记忆力测试', filename)}")
            except Exception as e:
                self._append_examiner_log(f"\n保存日志文件失败：{e}")
        
        self.memory_active = False
        self.status_var.set("正在测试：--")
        self.memory_score_var.set("记忆力得分：--")
        self.memory_button.config(text="记忆力测试")
        self._clear_prompt()
        self._cancel_memory_callbacks()
        self.current_trial = None
        self.memory_start_time = None
        self.memory_trial_count = 0

    def _schedule_next_memory_round(self, initial: bool = False):
        if not self.memory_active:
            return
        delay = random.randint(10, 20)
        if initial:
            delay = 1
        self.memory_prompt_after_id = self.after(delay * 1000, self._show_memory_prompt)

    def _show_memory_prompt(self):
        if not self.memory_active:
            return
        target = random.randint(1, 5)
        gesture = random.choice(self.GESTURES)
        prompt = f"控制无人机{target}号，执行动作{gesture}"
        self.prompt_var.set(prompt)
        display_time = time.monotonic()
        
        # 增加测试轮次
        self.memory_trial_count += 1
        
        # 记录命令
        log_text = f"记忆力测试{self.memory_trial_count}-命令：{prompt}"
        self._append_examiner_log(log_text)
        
        self.current_trial = {
            "target": target,
            "gesture": gesture,
            "display_time": display_time,
            "answered": False,
            "trial_number": self.memory_trial_count,
        }
        self.memory_hide_after_id = self.after(5000, self._clear_prompt)
        self.memory_timeout_after_id = self.after(30000, self._handle_memory_timeout)

    def _clear_prompt(self):
        self.prompt_var.set("")

    def _handle_memory_timeout(self):
        if not self.memory_active or not self.current_trial or self.current_trial.get("answered"):
            return
        # 超时情况，返回为空
        received_target = None
        received_gesture = None
        self._finalize_memory_trial(
            correct=False,
            reaction_time=30.0,
            received_target=received_target,
            received_gesture=received_gesture,
        )

    def _handle_control_output(self, line: str):
        if not self.memory_active or not self.current_trial or self.current_trial.get("answered"):
            return
        parts = line.split()
        if len(parts) < 2:
            return
        expected_target = self.current_trial["target"]
        expected_gesture = self.current_trial["gesture"]
        try:
            received_target = int(parts[0])
        except ValueError:
            return
        received_gesture = parts[1].upper()
        reaction_time = time.monotonic() - self.current_trial["display_time"]
        correct = received_target == expected_target and received_gesture == expected_gesture
        self._finalize_memory_trial(
            correct=correct,
            reaction_time=reaction_time,
            received_target=received_target,
            received_gesture=received_gesture,
        )

    def _finalize_memory_trial(
        self,
        correct: bool,
        reaction_time: float,
        received_target: Optional[int] = None,
        received_gesture: Optional[str] = None,
    ):
        if not self.current_trial:
            return
        self.current_trial["answered"] = True
        self._cancel_memory_callbacks()

        trial_number = self.current_trial["trial_number"]
        expected_target = self.current_trial["target"]
        expected_gesture = self.current_trial["gesture"]

        # 记录返回信息
        if received_target is not None and received_gesture is not None:
            return_text = f"控制无人机{received_target}号，执行动作{received_gesture}"
        else:
            return_text = "无返回（超时）"
        log_text = f"记忆力测试{trial_number}-返回：{return_text}"
        self._append_examiner_log(log_text)

        # 计算得分
        limited_rt = max(0.0, min(30.0, reaction_time))
        accuracy_score = 1.0 if correct else 0.0
        reaction_score = max(0.0, (30.0 - limited_rt) / 30.0)
        final_score = round(accuracy_score * 0.7 + reaction_score * 0.3, 3)
        self.memory_scores.append(final_score)

        avg_score = sum(self.memory_scores) / len(self.memory_scores)
        self.memory_score_var.set(f"记忆力得分：{avg_score:.3f}")

        # 记录结果信息
        accuracy_percent = "100%" if correct else "0%"
        result_text = (
            f"记忆力测试{trial_number}-结果：本次正确率{accuracy_percent}，"
            f"本次反应时间{reaction_time:.3f}秒，"
            f"本次记忆力得分{final_score:.3f}，"
            f"平均记忆力得分{avg_score:.3f}"
        )
        self._append_examiner_log(result_text)

        self.current_trial = None
        self._schedule_next_memory_round()

    def _cancel_memory_callbacks(self):
        for after_id in (self.memory_prompt_after_id, self.memory_hide_after_id, self.memory_timeout_after_id):
            if after_id is not None:
                try:
                    self.after_cancel(after_id)
                except Exception:
                    pass
        self.memory_prompt_after_id = None
        self.memory_hide_after_id = None
        self.memory_timeout_after_id = None

    def teardown(self):
        self._stop_memory_test()
        self.control_panel.unregister_output_listener(self._handle_control_output)


class PilotToolkitApp(tk.Tk):
    """飞行员作业能力测试工具箱主窗口"""

    def __init__(self):
        super().__init__()
        self.title("飞行员作业能力测试工具箱")
        self.geometry("960x600")
        self.minsize(720, 480)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build_layout()

    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        left_panel = ControlPanel(self, bd=2, relief="groove", padx=16, pady=16)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.control_panel = left_panel

        right_panel = CognitiveTestPanel(self, control_panel=left_panel, bd=2, relief="groove", padx=16, pady=16)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        self.cognitive_panel = right_panel

    def on_close(self):
        if isinstance(self.control_panel, ControlPanel):
            self.control_panel.stop_control()
        if hasattr(self, "cognitive_panel") and isinstance(self.cognitive_panel, CognitiveTestPanel):
            self.cognitive_panel.teardown()
        self.destroy()


def main():
    app = PilotToolkitApp()
    app.mainloop()


if __name__ == "__main__":
    main()

