"""
无人机控制器抽象基类
定义了无人机控制的统一接口
"""
from abc import ABC, abstractmethod
from typing import Optional


class DroneController(ABC):
    """无人机控制器抽象基类"""
    
    def __init__(self):
        self.is_connected = False
        self.is_flying = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        连接到无人机
        返回: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开与无人机的连接"""
        pass
    
    @abstractmethod
    async def takeoff(self, altitude: float = 5.0) -> dict:
        """
        起飞
        参数:
            altitude: 起飞高度（米）
        返回: 操作结果字典
        """
        pass
    
    @abstractmethod
    async def land(self) -> dict:
        """
        降落
        返回: 操作结果字典
        """
        pass
    
    @abstractmethod
    async def move_up(self, distance: float = 2.0) -> dict:
        """
        升高
        参数:
            distance: 升高距离（米）
        返回: 操作结果字典
        """
        pass
    
    @abstractmethod
    async def move_down(self, distance: float = 2.0) -> dict:
        """
        降低
        参数:
            distance: 降低距离（米）
        返回: 操作结果字典
        """
        pass
    
    @abstractmethod
    async def emergency_land(self) -> dict:
        """
        紧急降落（中断其他所有动作）
        返回: 操作结果字典
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> dict:
        """
        获取无人机状态
        返回: 状态信息字典
        """
        pass
