"""
AirSim无人机控制器实现
使用AirSim Python API控制模拟无人机
"""
import asyncio
from typing import Optional
from drone_controller import DroneController


class AirSimController(DroneController):
    """AirSim无人机控制器"""
    
    def __init__(self, ip: str = "127.0.0.1", port: int = 41451, vehicle_name: str = ""):
        """
        初始化AirSim控制器
        
        参数:
            ip: AirSim服务器IP地址
            port: AirSim服务器端口
            vehicle_name: 无人机名称（用于区分同一AirSim环境中的多个无人机）
                         留空表示使用默认无人机
        """
        super().__init__()
        self.ip = ip
        self.port = port
        self.vehicle_name = vehicle_name if vehicle_name else ""
        self.client = None
        self.default_altitude = 5.0
        self.move_step = 2.0
    
    async def connect(self) -> bool:
        """连接到AirSim"""
        try:
            import airsim
            
            # 在异步上下文中运行同步的AirSim连接
            loop = asyncio.get_event_loop()
            self.client = await loop.run_in_executor(
                None, 
                lambda: airsim.MultirotorClient(ip=self.ip, port=self.port)
            )

            await loop.run_in_executor(None, self.client.confirmConnection)
            
            # enableApiControl 和 armDisarm：vehicle_name 作为位置参数传递
            await loop.run_in_executor(
                None, 
                lambda: self.client.enableApiControl(True, self.vehicle_name)
            )
            await loop.run_in_executor(
                None,
                lambda: self.client.armDisarm(True, self.vehicle_name)
            )
            
            self.is_connected = True
            vehicle_info = f" [{self.vehicle_name}]" if self.vehicle_name else ""
            print(f"✓ 已连接到AirSim ({self.ip}:{self.port}){vehicle_info}")
            return True
            
        except ImportError:
            print("✗ 错误: 未安装airsim库，请运行: pip install airsim")
            return False
        except Exception as e:
            print(f"✗ 连接AirSim失败: {e}")
            return False
    
    async def disconnect(self):
        """断开AirSim连接"""
        if self.client and self.is_connected:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.client.armDisarm(False, self.vehicle_name)
                )
                await loop.run_in_executor(
                    None,
                    lambda: self.client.enableApiControl(False, self.vehicle_name)
                )
                vehicle_info = f" [{self.vehicle_name}]" if self.vehicle_name else ""
                print(f"✓ 已断开AirSim连接{vehicle_info}")
            except Exception as e:
                print(f"✗ 断开连接时出错: {e}")
            finally:
                self.is_connected = False
                self.is_flying = False
    
    async def takeoff(self, altitude: float = 5.0) -> dict:
        """起飞"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if self.is_flying:
            return {"success": False, "message": "无人机已经在飞行中"}
        
        try:
            loop = asyncio.get_event_loop()
            print(f"正在起飞到 {altitude} 米...")
            
            # 执行起飞
            await loop.run_in_executor(
                None,
                lambda: self.client.takeoffAsync(60, self.vehicle_name).join()
            )
            
            # 飞到指定高度
            vehicle_name = self.vehicle_name
            await loop.run_in_executor(
                None,
                lambda: self.client.moveToZAsync(-altitude, 2, vehicle_name=vehicle_name).join()
            )
            
            self.is_flying = True
            self.default_altitude = altitude
            print(f"✓ 起飞成功，当前高度: {altitude} 米")
            return {"success": True, "message": f"起飞成功，高度: {altitude}米"}
            
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
            loop = asyncio.get_event_loop()
            print("正在降落...")
            
            await loop.run_in_executor(
                None,
                lambda: self.client.landAsync(60, self.vehicle_name).join()
            )
            
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
            loop = asyncio.get_event_loop()
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            current_z = state.kinematics_estimated.position.z_val
            new_z = current_z - distance  # AirSim中Z轴向下为正
            
            print(f"正在升高 {distance} 米...")
            
            vehicle_name = self.vehicle_name
            await loop.run_in_executor(
                None,
                lambda: self.client.moveToZAsync(new_z, 1, vehicle_name=vehicle_name).join()
            )
            
            print(f"✓ 升高成功 {distance} 米")
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
            loop = asyncio.get_event_loop()
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            current_z = state.kinematics_estimated.position.z_val
            new_z = current_z + distance  # AirSim中Z轴向下为正
            
            # 确保不会降到地面以下
            if new_z > -0.5:
                new_z = -0.5
            
            print(f"正在降低 {distance} 米...")
            
            vehicle_name = self.vehicle_name
            await loop.run_in_executor(
                None,
                lambda: self.client.moveToZAsync(new_z, 1, vehicle_name=vehicle_name).join()
            )
            
            print(f"✓ 降低成功 {distance} 米")
            return {"success": True, "message": f"降低 {distance} 米成功"}
            
        except Exception as e:
            print(f"✗ 降低失败: {e}")
            return {"success": False, "message": f"降低失败: {str(e)}"}
    
    async def emergency_land(self) -> dict:
        """紧急降落"""
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        try:
            loop = asyncio.get_event_loop()
            print("!!! 紧急降落 !!!")
            
            # 取消所有当前动作
            await loop.run_in_executor(
                None,
                lambda: self.client.cancelLastTask(self.vehicle_name)
            )
            
            # 立即降落
            await loop.run_in_executor(
                None,
                lambda: self.client.landAsync(60, self.vehicle_name).join()
            )
            
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
            loop = asyncio.get_event_loop()
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            
            position = state.kinematics_estimated.position
            velocity = state.kinematics_estimated.linear_velocity
            
            status = {
                "connected": True,
                "flying": self.is_flying,
                "position": {
                    "x": position.x_val,
                    "y": position.y_val,
                    "z": -position.z_val  # 转换为正常的高度表示
                },
                "velocity": {
                    "x": velocity.x_val,
                    "y": velocity.y_val,
                    "z": velocity.z_val
                }
            }
            
            if self.vehicle_name:
                status["vehicle_name"] = self.vehicle_name
            
            return status
        except Exception as e:
            print(f"✗ 获取状态失败: {e}")
            return {"connected": self.is_connected, "flying": self.is_flying, "error": str(e)}
