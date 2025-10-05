"""
多无人机集群管理器
管理多个无人机分组和实例
"""
import asyncio
from typing import Dict, List, Optional
from drone_controller import DroneController
from airsim_controller import AirSimController
from real_drone_controller import RealDroneController


class DroneFleetManager:
    """多无人机集群管理器"""
    
    def __init__(self):
        # 存储结构: {group_name: {drone_id: controller}}
        self.fleets: Dict[str, Dict[str, DroneController]] = {}
        self.is_initialized = False
    
    async def initialize_fleet(self, fleet_config: dict):
        """
        初始化无人机集群
        
        参数:
            fleet_config: 集群配置字典
            格式: {
                "group_name": {
                    "type": "airsim" or "real",
                    "drones": [
                        {"id": "1", "connection": "127.0.0.1:41451"},
                        {"id": "2", "connection": "127.0.0.1:41452"},
                        ...
                    ]
                }
            }
        """
        print("\n正在初始化无人机集群...")
        
        for group_name, group_config in fleet_config.items():
            # 跳过以下划线开头的配置项（注释、说明等）
            if group_name.startswith("_"):
                continue
            
            # 确保group_config是字典类型
            if not isinstance(group_config, dict):
                print(f"⚠ 警告: 分组 '{group_name}' 配置格式错误，跳过")
                continue
            
            drone_type = group_config.get("type", "airsim")
            drones_config = group_config.get("drones", [])
            
            if not drones_config:
                print(f"⚠ 警告: 分组 '{group_name}' 没有配置无人机")
                continue
            
            print(f"\n初始化分组: {group_name} (类型: {drone_type})")
            self.fleets[group_name] = {}
            
            # 并行初始化该分组中的所有无人机
            tasks = []
            for drone_config in drones_config:
                drone_id = str(drone_config.get("id", ""))
                connection = drone_config.get("connection", "")
                
                if not drone_id:
                    print(f"  ✗ 跳过: 无人机配置缺少ID")
                    continue
                
                task = self._initialize_drone(
                    group_name, 
                    drone_id, 
                    drone_type, 
                    connection
                )
                tasks.append(task)
            
            # 等待该分组所有无人机初始化完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计成功/失败
            success_count = sum(1 for r in results if r is True)
            fail_count = len(results) - success_count
            
            print(f"  分组 '{group_name}' 初始化完成: ✓ {success_count} 成功, ✗ {fail_count} 失败")
        
        self.is_initialized = True
        
        # 打印总体统计
        total_groups = len(self.fleets)
        total_drones = sum(len(drones) for drones in self.fleets.values())
        print(f"\n✓ 集群初始化完成: {total_groups} 个分组, 共 {total_drones} 架无人机\n")
    
    async def _initialize_drone(
        self, 
        group_name: str, 
        drone_id: str, 
        drone_type: str, 
        connection: str
    ) -> bool:
        """初始化单个无人机"""
        try:
            # 创建控制器
            if drone_type == "airsim":
                # AirSim: connection格式为 "ip:port:vehicle_name" 或 "ip:port"
                # 多个无人机时必须指定vehicle_name
                parts = connection.split(":")
                
                if len(parts) >= 3:
                    # 格式: ip:port:vehicle_name
                    ip = parts[0]
                    port = int(parts[1])
                    vehicle_name = parts[2]
                    controller = AirSimController(ip=ip, port=port, vehicle_name=vehicle_name)
                elif len(parts) == 2:
                    # 格式: ip:port (单机模式，使用默认vehicle)
                    ip = parts[0]
                    port = int(parts[1])
                    controller = AirSimController(ip=ip, port=port, vehicle_name="")
                else:
                    # 只有vehicle_name或其他格式
                    # 假设是vehicle_name，使用默认ip和port
                    controller = AirSimController(vehicle_name=connection)
                    
            elif drone_type == "real":
                # 真实飞控: connection为连接字符串
                controller = RealDroneController(connection_string=connection)
            else:
                print(f"  ✗ [{group_name}:{drone_id}] 不支持的无人机类型: {drone_type}")
                return False
            
            # 连接无人机
            success = await controller.connect()
            
            if success:
                self.fleets[group_name][drone_id] = controller
                print(f"  ✓ [{group_name}:{drone_id}] 已连接")
                return True
            else:
                print(f"  ✗ [{group_name}:{drone_id}] 连接失败")
                return False
                
        except Exception as e:
            print(f"  ✗ [{group_name}:{drone_id}] 初始化失败: {e}")
            return False
    
    async def cleanup(self):
        """清理所有无人机连接"""
        print("\n正在关闭所有无人机连接...")
        
        tasks = []
        for group_name, drones in self.fleets.items():
            for drone_id, controller in drones.items():
                if controller.is_connected:
                    # 如果在飞行，先紧急降落
                    if controller.is_flying:
                        tasks.append(self._emergency_land_drone(group_name, drone_id, controller))
                    else:
                        tasks.append(controller.disconnect())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        print("✓ 所有无人机已断开连接\n")
    
    async def _emergency_land_drone(self, group_name: str, drone_id: str, controller: DroneController):
        """单个无人机紧急降落"""
        try:
            print(f"  ! [{group_name}:{drone_id}] 执行紧急降落")
            await controller.emergency_land()
            await controller.disconnect()
        except Exception as e:
            print(f"  ✗ [{group_name}:{drone_id}] 紧急降落失败: {e}")
    
    def get_controller(self, group: str, drone_id: Optional[str] = None) -> Optional[DroneController]:
        """
        获取单个无人机控制器
        
        参数:
            group: 分组名称
            drone_id: 无人机ID，如果为None则返回None
        
        返回:
            DroneController 或 None
        """
        if group not in self.fleets:
            return None
        
        if drone_id is None:
            return None
        
        return self.fleets[group].get(str(drone_id))
    
    def get_group_controllers(self, group: str) -> List[DroneController]:
        """
        获取整个分组的所有无人机控制器
        
        参数:
            group: 分组名称
        
        返回:
            DroneController列表
        """
        if group not in self.fleets:
            return []
        
        return list(self.fleets[group].values())
    
    def get_all_controllers(self) -> List[DroneController]:
        """获取所有无人机控制器"""
        controllers = []
        for drones in self.fleets.values():
            controllers.extend(drones.values())
        return controllers
    
    async def execute_command(
        self, 
        command: str, 
        group: str, 
        drone_id: Optional[str] = None,
        **kwargs
    ) -> dict:
        """
        执行控制命令
        
        参数:
            command: 命令名称 (takeoff, land, move_up, move_down)
            group: 分组名称
            drone_id: 无人机ID，如果为None则控制整个分组
            **kwargs: 命令参数
        
        返回:
            执行结果字典
        """
        # 检查分组是否存在
        if group not in self.fleets:
            return {
                "success": False,
                "message": f"分组 '{group}' 不存在",
                "available_groups": list(self.fleets.keys())
            }
        
        # 确定目标控制器
        if drone_id is None or drone_id == "":
            # 控制整个分组
            controllers = self.get_group_controllers(group)
            target_info = f"group:{group} (全部 {len(controllers)} 架)"
        else:
            # 控制单个无人机
            controller = self.get_controller(group, drone_id)
            if controller is None:
                return {
                    "success": False,
                    "message": f"无人机 '{group}:{drone_id}' 不存在",
                    "available_ids": list(self.fleets[group].keys())
                }
            controllers = [controller]
            target_info = f"group:{group}, id:{drone_id}"
        
        if not controllers:
            return {
                "success": False,
                "message": f"分组 '{group}' 中没有可用的无人机"
            }
        
        print(f"\n执行命令: {command} -> {target_info}")
        
        # 并行执行命令
        tasks = []
        for ctrl in controllers:
            if command == "takeoff":
                tasks.append(ctrl.takeoff(**kwargs))
            elif command == "land":
                tasks.append(ctrl.land(**kwargs))
            elif command == "move_up":
                tasks.append(ctrl.move_up(**kwargs))
            elif command == "move_down":
                tasks.append(ctrl.move_down(**kwargs))
            elif command == "emergency_land":
                tasks.append(ctrl.emergency_land(**kwargs))
            else:
                return {
                    "success": False,
                    "message": f"未知命令: {command}"
                }
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success", False))
        fail_count = len(results) - success_count
        
        all_success = success_count == len(results)
        
        return {
            "success": all_success,
            "message": f"命令执行完成: ✓ {success_count} 成功, ✗ {fail_count} 失败",
            "target": target_info,
            "details": [r for r in results if isinstance(r, dict)],
            "total": len(results),
            "success_count": success_count,
            "fail_count": fail_count
        }
    
    async def get_status(self, group: Optional[str] = None, drone_id: Optional[str] = None) -> dict:
        """
        获取状态信息
        
        参数:
            group: 分组名称，如果为None则返回所有分组状态
            drone_id: 无人机ID，如果为None则返回整个分组状态
        
        返回:
            状态信息字典
        """
        if group is None:
            # 返回所有分组的概览
            status = {
                "groups": {}
            }
            
            for group_name, drones in self.fleets.items():
                status["groups"][group_name] = {
                    "total": len(drones),
                    "connected": sum(1 for d in drones.values() if d.is_connected),
                    "flying": sum(1 for d in drones.values() if d.is_flying),
                    "drones": list(drones.keys())
                }
            
            return status
        
        # 检查分组是否存在
        if group not in self.fleets:
            return {
                "error": f"分组 '{group}' 不存在",
                "available_groups": list(self.fleets.keys())
            }
        
        # 返回特定分组或无人机的状态
        if drone_id is None or drone_id == "":
            # 返回整个分组的详细状态
            status = {
                "group": group,
                "drones": {}
            }
            
            for did, controller in self.fleets[group].items():
                status["drones"][did] = await controller.get_status()
            
            return status
        else:
            # 返回单个无人机的状态
            controller = self.get_controller(group, drone_id)
            if controller is None:
                return {
                    "error": f"无人机 '{group}:{drone_id}' 不存在",
                    "available_ids": list(self.fleets[group].keys())
                }
            
            return await controller.get_status()
    
    def get_fleet_info(self) -> dict:
        """获取集群信息"""
        info = {
            "total_groups": len(self.fleets),
            "groups": {}
        }
        
        for group_name, drones in self.fleets.items():
            info["groups"][group_name] = {
                "total_drones": len(drones),
                "drone_ids": list(drones.keys()),
                "connected": sum(1 for d in drones.values() if d.is_connected),
                "flying": sum(1 for d in drones.values() if d.is_flying)
            }
        
        total_drones = sum(len(drones) for drones in self.fleets.values())
        info["total_drones"] = total_drones
        
        return info
