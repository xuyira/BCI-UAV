"""
真实飞控无人机控制器实现
使用DroneKit和pymavlink控制真实无人机
"""
import asyncio
import time
from typing import Optional
from drone_controller import DroneController


class RealDroneController(DroneController):
    """真实飞控无人机控制器（使用DroneKit）"""
    
    def __init__(self, connection_string: str = "udp:127.0.0.1:14550"):
        """
        初始化真实飞控控制器
        参数:
            connection_string: 连接字符串，例如:
                - "udp:127.0.0.1:14550" (SITL模拟)
                - "/dev/ttyACM0" (串口连接)
                - "tcp:127.0.0.1:5760" (TCP连接)
                - "com3" (Windows串口)
        """
        super().__init__()
        self.connection_string = connection_string
        self.vehicle = None
        self.default_altitude = 5.0
        self.move_step = 2.0
    
    async def connect(self) -> bool:
        """连接到真实飞控"""
        try:
            from dronekit import connect as dronekit_connect
            
            print(f"正在连接到飞控: {self.connection_string}")
            
            loop = asyncio.get_event_loop()
            
            # 在异步上下文中连接
            self.vehicle = await loop.run_in_executor(
                None,
                lambda: dronekit_connect(self.connection_string, wait_ready=True, timeout=60)
            )
            
            self.is_connected = True
            
            # 打印飞控信息
            print(f"✓ 已连接到飞控")
            print(f"  - 固件版本: {self.vehicle.version}")
            print(f"  - 飞行模式: {self.vehicle.mode.name}")
            print(f"  - 是否可以解锁: {self.vehicle.is_armable}")
            print(f"  - GPS: {self.vehicle.gps_0}")
            
            return True
            
        except ImportError:
            print("✗ 错误: 未安装dronekit库，请运行: pip install dronekit pymavlink")
            return False
        except Exception as e:
            print(f"✗ 连接飞控失败: {e}")
            return False
    
    async def disconnect(self):
        """断开飞控连接"""
        if self.vehicle and self.is_connected:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.vehicle.close)
                print("✓ 已断开飞控连接")
            except Exception as e:
                print(f"✗ 断开连接时出错: {e}")
            finally:
                self.is_connected = False
                self.is_flying = False
    
    async def _arm_and_takeoff(self, target_altitude: float) -> bool:
        """解锁并起飞到指定高度"""
        from dronekit import VehicleMode
        
        loop = asyncio.get_event_loop()
        
        print("正在检查飞控状态...")
        
        # 等待飞控可以解锁
        timeout = 30
        start_time = time.time()
        while not self.vehicle.is_armable:
            if time.time() - start_time > timeout:
                print("✗ 飞控在规定时间内无法解锁")
                return False
            await asyncio.sleep(1)
        
        print("✓ 飞控可以解锁")
        
        # 切换到GUIDED模式
        print("切换到GUIDED模式...")
        await loop.run_in_executor(
            None,
            lambda: setattr(self.vehicle, 'mode', VehicleMode("GUIDED"))
        )
        
        # 等待模式切换
        while self.vehicle.mode.name != "GUIDED":
            await asyncio.sleep(0.5)
        
        print("✓ 已切换到GUIDED模式")
        
        # 解锁
        print("正在解锁...")
        self.vehicle.armed = True
        
        # 等待解锁完成
        while not self.vehicle.armed:
            await asyncio.sleep(0.5)
        
        print("✓ 解锁成功")
        
        # 起飞
        print(f"正在起飞到 {target_altitude} 米...")
        await loop.run_in_executor(
            None,
            lambda: self.vehicle.simple_takeoff(target_altitude)
        )
        
        # 等待到达目标高度
        while True:
            current_altitude = self.vehicle.location.global_relative_frame.alt
            print(f"  当前高度: {current_altitude:.1f} 米")
            
            if current_altitude >= target_altitude * 0.95:
                print(f"✓ 已到达目标高度: {current_altitude:.1f} 米")
                break
            
            await asyncio.sleep(1)
        
        return True
    
    async def takeoff(self, altitude: float = 5.0) -> dict:
        """起飞"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if self.is_flying:
            return {"success": False, "message": "无人机已经在飞行中"}
        
        try:
            success = await self._arm_and_takeoff(altitude)
            
            if success:
                self.is_flying = True
                self.default_altitude = altitude
                return {"success": True, "message": f"起飞成功，高度: {altitude}米"}
            else:
                return {"success": False, "message": "起飞失败"}
            
        except Exception as e:
            print(f"✗ 起飞失败: {e}")
            return {"success": False, "message": f"起飞失败: {str(e)}"}
    
    async def land(self) -> dict:
        """降落"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        # 改为警告而不是拒绝执行，因为is_flying可能与实际状态不同步
        if not self.is_flying:
            print("⚠ 警告: 内部状态显示未在飞行，但仍尝试执行降落命令")
        
        try:
            from dronekit import VehicleMode
            
            print("正在降落...")
            
            loop = asyncio.get_event_loop()
            
            # 切换到LAND模式
            await loop.run_in_executor(
                None,
                lambda: setattr(self.vehicle, 'mode', VehicleMode("LAND"))
            )
            
            # 等待降落完成
            while self.vehicle.armed:
                current_altitude = self.vehicle.location.global_relative_frame.alt
                print(f"  当前高度: {current_altitude:.1f} 米")
                await asyncio.sleep(1)
            
            self.is_flying = False
            print("✓ 降落成功")
            return {"success": True, "message": "降落成功"}
            
        except Exception as e:
            print(f"✗ 降落失败: {e}")
            return {"success": False, "message": f"降落失败: {str(e)}"}
    
    async def move_up(self, distance: float = 2.0) -> dict:
        """升高"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if not self.is_flying:
            return {"success": False, "message": "无人机未在飞行"}
        
        try:
            from dronekit import LocationGlobalRelative
            
            current_altitude = self.vehicle.location.global_relative_frame.alt
            target_altitude = current_altitude + distance
            
            print(f"正在从 {current_altitude:.1f} 米升高到 {target_altitude:.1f} 米...")
            
            loop = asyncio.get_event_loop()
            
            # 设置目标位置（保持当前经纬度，只改变高度）
            target_location = LocationGlobalRelative(
                self.vehicle.location.global_relative_frame.lat,
                self.vehicle.location.global_relative_frame.lon,
                target_altitude
            )
            
            await loop.run_in_executor(
                None,
                lambda: self.vehicle.simple_goto(target_location)
            )
            
            # 等待到达目标高度
            while True:
                current = self.vehicle.location.global_relative_frame.alt
                if abs(current - target_altitude) < 0.5:
                    break
                await asyncio.sleep(0.5)
            
            print(f"✓ 升高成功，当前高度: {self.vehicle.location.global_relative_frame.alt:.1f} 米")
            return {"success": True, "message": f"升高 {distance} 米成功"}
            
        except Exception as e:
            print(f"✗ 升高失败: {e}")
            return {"success": False, "message": f"升高失败: {str(e)}"}
    
    async def move_down(self, distance: float = 2.0) -> dict:
        """降低"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if not self.is_flying:
            return {"success": False, "message": "无人机未在飞行"}
        
        try:
            from dronekit import LocationGlobalRelative
            
            current_altitude = self.vehicle.location.global_relative_frame.alt
            target_altitude = max(1.0, current_altitude - distance)  # 最低保持1米
            
            print(f"正在从 {current_altitude:.1f} 米降低到 {target_altitude:.1f} 米...")
            
            loop = asyncio.get_event_loop()
            
            # 设置目标位置
            target_location = LocationGlobalRelative(
                self.vehicle.location.global_relative_frame.lat,
                self.vehicle.location.global_relative_frame.lon,
                target_altitude
            )
            
            await loop.run_in_executor(
                None,
                lambda: self.vehicle.simple_goto(target_location)
            )
            
            # 等待到达目标高度
            while True:
                current = self.vehicle.location.global_relative_frame.alt
                if abs(current - target_altitude) < 0.5:
                    break
                await asyncio.sleep(0.5)
            
            print(f"✓ 降低成功，当前高度: {self.vehicle.location.global_relative_frame.alt:.1f} 米")
            return {"success": True, "message": f"降低 {distance} 米成功"}
            
        except Exception as e:
            print(f"✗ 降低失败: {e}")
            return {"success": False, "message": f"降低失败: {str(e)}"}
    
    async def emergency_land(self) -> dict:
        """紧急降落"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        try:
            from dronekit import VehicleMode
            
            print("!!! 紧急降落 !!!")
            
            loop = asyncio.get_event_loop()
            
            # 立即切换到LAND模式
            await loop.run_in_executor(
                None,
                lambda: setattr(self.vehicle, 'mode', VehicleMode("LAND"))
            )
            
            # 等待降落
            timeout = 60
            start_time = time.time()
            while self.vehicle.armed:
                if time.time() - start_time > timeout:
                    print("警告: 紧急降落超时")
                    break
                await asyncio.sleep(0.5)
            
            self.is_flying = False
            print("✓ 紧急降落完成")
            return {"success": True, "message": "紧急降落完成"}
            
        except Exception as e:
            print(f"✗ 紧急降落失败: {e}")
            return {"success": False, "message": f"紧急降落失败: {str(e)}"}
    
    async def get_status(self) -> dict:
        """获取无人机状态"""
        if not self.is_connected:
            return {"connected": False, "flying": False}
        
        try:
            return {
                "connected": True,
                "flying": self.is_flying,
                "armed": self.vehicle.armed,
                "mode": self.vehicle.mode.name,
                "position": {
                    "lat": self.vehicle.location.global_relative_frame.lat,
                    "lon": self.vehicle.location.global_relative_frame.lon,
                    "alt": self.vehicle.location.global_relative_frame.alt
                },
                "velocity": {
                    "x": self.vehicle.velocity[0] if self.vehicle.velocity else 0,
                    "y": self.vehicle.velocity[1] if self.vehicle.velocity else 0,
                    "z": self.vehicle.velocity[2] if self.vehicle.velocity else 0
                },
                "battery": {
                    "voltage": self.vehicle.battery.voltage if self.vehicle.battery else None,
                    "level": self.vehicle.battery.level if self.vehicle.battery else None
                },
                "gps": str(self.vehicle.gps_0) if self.vehicle.gps_0 else "No GPS"
            }
        except Exception as e:
            print(f"✗ 获取状态失败: {e}")
            return {"connected": self.is_connected, "flying": self.is_flying, "error": str(e)}
