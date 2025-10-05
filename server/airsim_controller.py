"""
AirSim无人机控制器实现
使用AirSim Python API控制模拟无人机
"""
import asyncio
from typing import Optional
from drone_controller import DroneController


class AirSimController(DroneController):
    """AirSim无人机控制器"""
    
    def __init__(self, ip: str = "127.0.0.1", port: int = 41451, vehicle_name: str = "", drone_id: str = ""):
        """
        初始化AirSim控制器
        
        参数:
            ip: AirSim服务器IP地址
            port: AirSim服务器端口
            vehicle_name: 无人机名称（用于区分同一AirSim环境中的多个无人机）
                         留空表示使用默认无人机
            drone_id: 无人机ID（用于标识和日志记录）
        """
        super().__init__()
        self.ip = ip
        self.port = port
        self.vehicle_name = vehicle_name if vehicle_name else ""
        self.drone_id = drone_id if drone_id else ""
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
            info_parts = []
            if self.drone_id:
                info_parts.append(f"ID:{self.drone_id}")
            if self.vehicle_name:
                info_parts.append(f"Vehicle:{self.vehicle_name}")
            info_str = f" [{', '.join(info_parts)}]" if info_parts else ""
            print(f"✓ 已连接到AirSim ({self.ip}:{self.port}){info_str}")
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
                info_parts = []
                if self.drone_id:
                    info_parts.append(f"ID:{self.drone_id}")
                if self.vehicle_name:
                    info_parts.append(f"Vehicle:{self.vehicle_name}")
                info_str = f" [{', '.join(info_parts)}]" if info_parts else ""
                print(f"✓ 已断开AirSim连接{info_str}")
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
            
            # 先获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            current_z = state.kinematics_estimated.position.z_val
            target_z = -0.5  # 离地面0.5米

            
            # 如果当前高度高于0.5米，先快速下降到0.5米
            if current_z < target_z:
                print(f"  第一步: 快速下降到0.5米 (当前高度: {-current_z:.2f}米)")
                vehicle_name = self.vehicle_name
                await loop.run_in_executor(
                    None,
                    lambda: self.client.moveToZAsync(target_z, 1, vehicle_name=vehicle_name).join()  # 降低速度到2米/秒
                )

            else:
                print(f"  跳过第一步：当前已在0.5米或更低")
            
            # 然后调用land命令完成最后的降落
            print("  第二步: 执行land命令着陆")
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
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            current_z = state.kinematics_estimated.position.z_val
            target_z = -0.5  # 离地面0.5米

            
            # 如果当前高度高于0.5米，先紧急快速下降到0.5米
            if current_z < target_z:
                print(f"  第一步: 紧急快速下降到0.5米 (当前高度: {-current_z:.2f}米)")
                vehicle_name = self.vehicle_name
                await loop.run_in_executor(
                    None,
                    lambda: self.client.moveToZAsync(target_z, 1, vehicle_name=vehicle_name).join()  # 紧急模式速度3米/秒
                )
                
                # 验证位置
                state_after = await loop.run_in_executor(
                    None,
                    lambda: self.client.getMultirotorState(self.vehicle_name)
                )
                actual_z = state_after.kinematics_estimated.position.z_val
                print(f"  ✓ 下降完成，实际高度: {-actual_z:.2f}米")
            
            # 然后调用land命令完成最后的降落
            print("  第二步: 执行land命令着陆")
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
    
    async def fly_circle(self, diameter: float = 5.0, velocity: float = 3.0) -> dict:
        """
        飞行一个圆圈
        参数:
            diameter: 圆的直径（米）
            velocity: 飞行速度（米/秒）
        """
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if not self.is_flying:
            return {"success": False, "message": "无人机未在飞行"}
        
        try:
            import math
            loop = asyncio.get_event_loop()
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            center_x = state.kinematics_estimated.position.x_val
            center_y = state.kinematics_estimated.position.y_val
            current_z = state.kinematics_estimated.position.z_val
            
            # 计算圆周上的路径点
            radius = diameter / 2.0
            num_points = 16  # 圆周上的点数
            
            print(f"正在飞行圆圈（直径 {diameter} 米）...")
            print(f"  中心位置: x={center_x:.2f}, y={center_y:.2f}, z={current_z:.2f}")
            print(f"  半径: {radius:.2f} 米, 速度: {velocity} 米/秒")
            
            vehicle_name = self.vehicle_name

            # 飞行圆周
            for i in range(num_points + 1):  # +1 以回到起点
                angle = 2 * math.pi * i / num_points
                target_x = center_x + radius * math.cos(angle)
                target_y = center_y + radius * math.sin(angle)
                
                print(f"  -> 路径点 {i+1}/{num_points+1}: ({target_x:.2f}, {target_y:.2f})")
                
                await loop.run_in_executor(
                    None,
                    lambda x=target_x, y=target_y, z=current_z, v=velocity, vn=vehicle_name: 
                        self.client.moveToPositionAsync(x, y, z, v, vehicle_name=vn).join()
                )
            
            print(f"✓ 圆圈飞行完成")
            return {"success": True, "message": f"圆圈飞行完成（直径 {diameter} 米）"}
            
        except Exception as e:
            print(f"✗ 圆圈飞行失败: {e}")
            return {"success": False, "message": f"圆圈飞行失败: {str(e)}"}
    
    async def vertical_oscillate(self, distance: float = 2.0, cycles: int = 6, velocity: float = 1.0) -> dict:

        """
        上下往复运动
        参数:
            distance: 每次往复的距离（米）
            cycles: 往复次数
            velocity: 运动速度（米/秒）
        """
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if not self.is_flying:
            return {"success": False, "message": "无人机未在飞行"}
        direction = int(self.drone_id) % 2
        direction = -1 if direction == 0 else direction
        try:
            loop = asyncio.get_event_loop()
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            base_z = state.kinematics_estimated.position.z_val
            
            print(f"正在执行上下往复运动（{cycles} 次，幅度 {distance} 米）...")
            
            vehicle_name = self.vehicle_name
            
            for i in range(cycles):
                # 上升
                up_z = base_z - direction * (i%2) * distance  # AirSim中Z轴向下为正
                await loop.run_in_executor(
                    None,
                    lambda: self.client.moveToZAsync(up_z, velocity, vehicle_name=vehicle_name).join()
                )
                # 下降
                await loop.run_in_executor(
                    None,
                    lambda: self.client.moveToZAsync(base_z, velocity, vehicle_name=vehicle_name).join()
                )
                
                print(f"  完成第 {i+1}/{cycles} 次往复")
            
            print(f"✓ 上下往复运动完成")
            return {"success": True, "message": f"上下往复运动完成（{cycles} 次，幅度 {distance} 米）"}
            
        except Exception as e:
            print(f"✗ 上下往复运动失败: {e}")
            return {"success": False, "message": f"上下往复运动失败: {str(e)}"}
    
    async def spiral_ascent(self, diameter: float = 4.0, height: float = 3.0, velocity: float = 2.0) -> dict:
        """
        螺旋上升 - 边飞圆圈边上升
        参数:
            diameter: 螺旋的直径（米）
            height: 上升的总高度（米）
            velocity: 飞行速度（米/秒）
        """
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if not self.is_flying:
            return {"success": False, "message": "无人机未在飞行"}
        
        try:
            import math
            loop = asyncio.get_event_loop()
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            center_x = state.kinematics_estimated.position.x_val
            center_y = state.kinematics_estimated.position.y_val
            start_z = state.kinematics_estimated.position.z_val
            
            radius = diameter / 2.0
            num_points = 20  # 螺旋路径点数
            
            print(f"正在执行螺旋上升（直径 {diameter}米，上升 {height}米）...")
            print(f"  起始位置: x={center_x:.2f}, y={center_y:.2f}, 高度={-start_z:.2f}米")
            
            vehicle_name = self.vehicle_name
            
            # 螺旋上升：每个点的高度逐渐增加
            for i in range(num_points + 1):
                angle = 2 * math.pi * i / num_points
                target_x = center_x + radius * math.cos(angle)
                target_y = center_y + radius * math.sin(angle)
                # 线性插值高度：从 start_z 到 start_z - height
                target_z = start_z - (height * i / num_points)
                
                if i % 5 == 0:  # 每5个点打印一次
                    print(f"  -> 路径点 {i+1}/{num_points+1}: 高度 {-target_z:.2f}米")
                
                await loop.run_in_executor(
                    None,
                    lambda x=target_x, y=target_y, z=target_z, v=velocity, vn=vehicle_name: 
                        self.client.moveToPositionAsync(x, y, z, v, vehicle_name=vn).join()
                )
            
            print(f"✓ 螺旋上升完成，总上升 {height}米")
            return {"success": True, "message": f"螺旋上升完成（直径 {diameter}米，上升 {height}米）"}
            
        except Exception as e:
            print(f"✗ 螺旋上升失败: {e}")
            return {"success": False, "message": f"螺旋上升失败: {str(e)}"}
    
    async def figure_eight(self, size: float = 3.0, velocity: float = 2.5) -> dict:
        """
        8字飞行 - 飞一个∞形状的轨迹
        参数:
            size: 8字的大小（每个圆的半径，米）
            velocity: 飞行速度（米/秒）
        """
        if not self.is_connected:
            return {"success": False, "message": "未连接到无人机"}
        
        if not self.is_flying:
            return {"success": False, "message": "无人机未在飞行"}
        
        try:
            import math
            loop = asyncio.get_event_loop()
            
            # 获取当前位置
            state = await loop.run_in_executor(
                None,
                lambda: self.client.getMultirotorState(self.vehicle_name)
            )
            center_x = state.kinematics_estimated.position.x_val
            center_y = state.kinematics_estimated.position.y_val
            current_z = state.kinematics_estimated.position.z_val
            
            radius = size / 2.0
            num_points_per_circle = 16  # 每个圆的点数
            
            print(f"正在执行8字飞行（大小 {size}米）...")
            print(f"  中心位置: x={center_x:.2f}, y={center_y:.2f}, 高度={-current_z:.2f}米")
            
            vehicle_name = self.vehicle_name
            
            # 8字由两个圆组成，中心分别在左右
            # 左圆：中心在 (center_x - radius, center_y)
            # 右圆：中心在 (center_x + radius, center_y)
            
            all_points = []
            
            # 第一个圆（右边，顺时针）
            left_center_x = center_x - radius
            for i in range(num_points_per_circle):
                angle = 2 * math.pi * i / num_points_per_circle
                x = left_center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                all_points.append((x, y))
            
            # 第二个圆（左边，逆时针）
            right_center_x = center_x + radius
            for i in range(num_points_per_circle):
                angle = -2 * math.pi * i / num_points_per_circle  # 逆时针
                x = right_center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                all_points.append((x, y))
            
            print(f"  路径点总数: {len(all_points)}")
            
            # 飞行8字轨迹
            for idx, (target_x, target_y) in enumerate(all_points):
                if idx % 8 == 0:
                    print(f"  -> 进度: {idx}/{len(all_points)}")
                
                await loop.run_in_executor(
                    None,
                    lambda x=target_x, y=target_y, z=current_z, v=velocity, vn=vehicle_name: 
                        self.client.moveToPositionAsync(x, y, z, v, vehicle_name=vn).join()
                )
            
            # 回到起点
            await loop.run_in_executor(
                None,
                lambda x=center_x, y=center_y, z=current_z, v=velocity, vn=vehicle_name: 
                    self.client.moveToPositionAsync(x, y, z, v, vehicle_name=vn).join()
            )
            
            print(f"✓ 8字飞行完成")
            return {"success": True, "message": f"8字飞行完成（大小 {size}米）"}
            
        except Exception as e:
            print(f"✗ 8字飞行失败: {e}")
            return {"success": False, "message": f"8字飞行失败: {str(e)}"}
    
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
            
            if self.drone_id:
                status["drone_id"] = self.drone_id
            if self.vehicle_name:
                status["vehicle_name"] = self.vehicle_name
            
            return status
        except Exception as e:
            print(f"✗ 获取状态失败: {e}")
            return {"connected": self.is_connected, "flying": self.is_flying, "error": str(e)}
