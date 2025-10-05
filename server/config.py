"""
配置文件
管理无人机控制系统的配置参数
"""
import os
import json


class Config:
    """配置类"""
    
    # HTTP服务器配置
    HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
    
    # 工作模式: "single" (单机) 或 "fleet" (集群)
    MODE = os.getenv("MODE", "single")
    
    # ===== 单机模式配置 =====
    # 无人机类型: "airsim" 或 "real"
    DRONE_TYPE = os.getenv("DRONE_TYPE", "airsim")
    
    # AirSim配置
    #AIRSIM_IP = os.getenv("AIRSIM_IP", "127.0.0.1")
    AIRSIM_IP = os.getenv("AIRSIM_IP", "172.26.0.1")

    AIRSIM_PORT = int(os.getenv("AIRSIM_PORT", "41451"))
    
    # 真实飞控配置
    # 连接字符串示例:
    # - "udp:127.0.0.1:14550" (SITL模拟)
    # - "/dev/ttyACM0" (Linux串口)
    # - "com3" (Windows串口)
    # - "tcp:127.0.0.1:5760" (TCP连接)
    REAL_DRONE_CONNECTION = os.getenv("REAL_DRONE_CONNECTION", "udp:127.0.0.1:14550")
    
    # ===== 集群模式配置 =====
    # 集群配置文件路径
    FLEET_CONFIG_FILE = os.getenv("FLEET_CONFIG_FILE", "fleet_config.json")
    
    # 飞行参数
    DEFAULT_ALTITUDE = float(os.getenv("DEFAULT_ALTITUDE", "5.0"))  # 默认起飞高度（米）
    MOVE_STEP = float(os.getenv("MOVE_STEP", "2.0"))  # 升高/降低步长（米）
    
    @classmethod
    def load_fleet_config(cls, config_file: str = None) -> dict:
        """
        加载集群配置文件
        
        参数:
            config_file: 配置文件路径，如果为None则使用默认路径
        
        返回:
            集群配置字典
        """
        if config_file is None:
            config_file = cls.FLEET_CONFIG_FILE
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except FileNotFoundError:
            print(f"✗ 集群配置文件不存在: {config_file}")
            print(f"提示: 请创建配置文件或参考 fleet_config.example.json")
            return {}
        except json.JSONDecodeError as e:
            print(f"✗ 集群配置文件格式错误: {e}")
            return {}
        except Exception as e:
            print(f"✗ 加载集群配置失败: {e}")
            return {}
    
    @classmethod
    def get_config_info(cls) -> dict:
        """获取当前配置信息"""
        info = {
            "http_server": f"{cls.HTTP_HOST}:{cls.HTTP_PORT}",
            "mode": cls.MODE,
            "flight_params": {
                "default_altitude": cls.DEFAULT_ALTITUDE,
                "move_step": cls.MOVE_STEP
            }
        }
        
        if cls.MODE == "single":
            info["drone_type"] = cls.DRONE_TYPE
            if cls.DRONE_TYPE == "airsim":
                info["airsim"] = {
                    "ip": cls.AIRSIM_IP,
                    "port": cls.AIRSIM_PORT
                }
            else:
                info["real_drone"] = {
                    "connection": cls.REAL_DRONE_CONNECTION
                }
        else:  # fleet mode
            info["fleet_config_file"] = cls.FLEET_CONFIG_FILE
        
        return info
    
    @classmethod
    def print_config(cls):
        """打印配置信息"""
        print("\n" + "="*50)
        print("无人机控制系统配置")
        print("="*50)
        print(f"HTTP服务器: {cls.HTTP_HOST}:{cls.HTTP_PORT}")
        print(f"工作模式: {cls.MODE.upper()}")
        
        if cls.MODE == "single":
            print(f"无人机类型: {cls.DRONE_TYPE.upper()}")
            
            if cls.DRONE_TYPE == "airsim":
                print(f"AirSim地址: {cls.AIRSIM_IP}:{cls.AIRSIM_PORT}")
            else:
                print(f"飞控连接: {cls.REAL_DRONE_CONNECTION}")
        else:  # fleet mode
            print(f"集群配置文件: {cls.FLEET_CONFIG_FILE}")
        
        print(f"默认起飞高度: {cls.DEFAULT_ALTITUDE} 米")
        print(f"升降步长: {cls.MOVE_STEP} 米")
        print("="*50 + "\n")
