#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手势识别模块
基于 gestures.txt 的规则进行手势识别
"""

from typing import Optional


class GestureRecognizer:
    """基于 gestures.txt 的规则。"""

    def __init__(self):
        # 阈值常量（直接来源于 gestures.txt）
        self.LOW_1000 = 1000
        self.HIGH_1500 = 1500
        self.HIGH_2400 = 2400

    def _is_fist(self, f):
        return (
            f['thumb'] < self.LOW_1000 and
            f['index'] < self.LOW_1000 and
            f['middle'] < self.LOW_1000 and
            f['ring'] < self.LOW_1000 and
            f['pinky'] < self.LOW_1000
        )

    def _is_five(self, f):
        return (
            f['thumb'] > self.HIGH_2400 and
            f['index'] > self.HIGH_2400 and
            f['middle'] > self.HIGH_2400 and
            f['ring'] > self.HIGH_2400 and
            f['pinky'] > self.HIGH_2400
        )

    def _is_good(self, f):
        return (
            f['thumb'] > self.HIGH_2400 and
            f['index'] < self.LOW_1000 and
            f['middle'] < self.LOW_1000 and
            f['ring'] < self.LOW_1000 and
            f['pinky'] < self.LOW_1000
        )

    def _is_gun(self, f):
        return (
            f['thumb'] > self.HIGH_2400 and
            f['index'] > self.HIGH_2400 and
            f['middle'] > self.HIGH_2400 and
            f['ring'] < self.HIGH_1500 and
            f['pinky'] < self.HIGH_1500
        )

    def _is_f_ck(self, f):
        return (
            f['thumb'] < self.LOW_1000 and
            f['index'] < self.LOW_1000 and
            f['middle'] > self.HIGH_1500 and
            f['ring'] < self.LOW_1000 and
            f['pinky'] < self.LOW_1000
        )

    def _is_rock(self, f):
        # 小指"无限制"，只检查其它四个
        return (
            f['thumb'] < self.HIGH_1500 and
            f['index'] > self.HIGH_2400 and
            f['middle'] < self.HIGH_1500 and
            f['ring'] < self.HIGH_1500
        )

    def _gesture_label(self, fingers):
        # 手势优先顺序：按文件列出先后顺序
        if self._is_fist(fingers):
            return 'FIST'
        if self._is_five(fingers):
            return 'FIVE'
        if self._is_good(fingers):
            return 'GOOD'
        if self._is_gun(fingers):
            return 'GUN'
        if self._is_f_ck(fingers):
            return 'F_CK'
        if self._is_rock(fingers):
            return 'ROCK'
        return None

    def recognize(self, data) -> Optional[str]:
        # 仅手势
        label = self._gesture_label(data['fingers'])
        if label is not None:
            return label
        return None
