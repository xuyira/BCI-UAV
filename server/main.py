"""
无人机控制HTTP服务器主程序
接收HTTP请求控制无人机（支持单机和集群模式）
"""
import asyncio
import signal
import sys
import argparse
from aiohttp import web
import json

from config import Config
from airsim_controller import AirSimController
from real_drone_controller import RealDroneController
from drone_fleet_manager import DroneFleetManager


class DroneControlServer:
    """无人机控制服务器（支持单机和集群模式）"""
    
    def __init__(self, mode: str = "single", drone_type: str = "airsim", fleet_config: dict = None):
        self.mode = mode
        self.drone_type = drone_type
        self.controller = None  # 单机模式使用
        self.fleet_manager = None  # 集群模式使用
        self.fleet_config = fleet_config or {}
        
        self.app = web.Application()
        self.runner = None
        self.shutdown_event = asyncio.Event()
        
        # 设置路由
        self.app.router.add_get('/', self.handle_root)
        self.app.router.add_get('/control', self.handle_control)
        self.app.router.add_post('/control', self.handle_control)
        self.app.router.add_get('/status', self.handle_status)
        self.app.router.add_get('/config', self.handle_config)
        self.app.router.add_get('/fleet', self.handle_fleet_info)
    
    async def initialize(self):
        """初始化无人机控制器"""
        if self.mode == "single":
            await self._initialize_single_mode()
        elif self.mode == "fleet":
            await self._initialize_fleet_mode()
        else:
            raise ValueError(f"不支持的工作模式: {self.mode}")
    
    async def _initialize_single_mode(self):
        """初始化单机模式"""
        print("\n正在初始化单机模式...")
        
        if self.drone_type == "airsim":
            self.controller = AirSimController(
                ip=Config.AIRSIM_IP,
                port=Config.AIRSIM_PORT
            )
        elif self.drone_type == "real":
            self.controller = RealDroneController(
                connection_string=Config.REAL_DRONE_CONNECTION
            )
        else:
            raise ValueError(f"不支持的无人机类型: {self.drone_type}")
        
        # 连接到无人机
        success = await self.controller.connect()
        if not success:
            raise Exception("无法连接到无人机")
        
        print("✓ 单机模式初始化成功\n")
    
    async def _initialize_fleet_mode(self):
        """初始化集群模式"""
        print("\n正在初始化集群模式...")
        
        self.fleet_manager = DroneFleetManager()
        
        if not self.fleet_config:
            raise Exception("集群模式需要提供集群配置")
        
        await self.fleet_manager.initialize_fleet(self.fleet_config)
        
        print("✓ 集群模式初始化成功\n")
    
    async def cleanup(self):
        """清理资源并安全关闭"""
        print("\n正在关闭服务器...")
        
        if self.mode == "single":
            # 单机模式清理
            if self.controller and self.controller.is_connected:
                if self.controller.is_flying:
                    print("检测到无人机仍在飞行，执行紧急降落...")
                    await self.controller.emergency_land()
                
                # 断开连接
                await self.controller.disconnect()
        
        elif self.mode == "fleet":
            # 集群模式清理
            if self.fleet_manager:
                await self.fleet_manager.cleanup()
        
        # 关闭HTTP服务器
        if self.runner:
            await self.runner.cleanup()
        
        print("✓ 服务器已安全关闭\n")
    
    async def handle_root(self, request):
        """处理根路径请求"""
        if self.mode == "single":
            html = self._get_single_mode_html()
        else:
            html = self._get_fleet_mode_html()
        
        return web.Response(text=html, content_type='text/html')
    
    def _get_single_mode_html(self):
        """单机模式的HTML界面"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>无人机控制系统 - 单机模式</title>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .controls {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin: 30px 0;
                }
                button {
                    padding: 15px 30px;
                    font-size: 16px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                .btn-takeoff { background: #4CAF50; color: white; }
                .btn-land { background: #f44336; color: white; }
                .btn-up { background: #2196F3; color: white; }
                .btn-down { background: #FF9800; color: white; }
                .btn-circle { background: #9C27B0; color: white; }
                .btn-oscillate { background: #00BCD4; color: white; }
                .btn-spiral { background: #E91E63; color: white; }
                .btn-eight { background: #3F51B5; color: white; }
                button:hover { opacity: 0.8; transform: scale(1.05); }
                .status {
                    background: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin-top: 20px;
                }
                .response {
                    margin-top: 15px;
                    padding: 10px;
                    border-radius: 5px;
                    font-family: monospace;
                    white-space: pre-wrap;
                }
                .success { background: #c8e6c9; }
                .error { background: #ffcdd2; }
                .info {
                    text-align: center;
                    color: #666;
                    margin-top: 20px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚁 无人机控制系统 - 单机模式</h1>
                
                <div class="status">
                    <strong>系统信息:</strong><br>
                    工作模式: <span id="mode">单机模式</span><br>
                    无人机类型: <span id="drone-type">加载中...</span><br>
                    连接状态: <span id="connection">加载中...</span><br>
                    飞行状态: <span id="flying">加载中...</span>
                </div>
                
                <div class="controls">
                    <button class="btn-takeoff" onclick="sendCommand(1)">起飞 (Takeoff)</button>
                    <button class="btn-land" onclick="sendCommand(2)">降落 (Land)</button>
                    <button class="btn-up" onclick="sendCommand(7)">升高 (Move Up)</button>
                    <button class="btn-down" onclick="sendCommand(8)">降低 (Move Down)</button>
                    <button class="btn-circle" onclick="sendCommand(3)">飞圈 (Circle)</button>
                    <button class="btn-oscillate" onclick="sendCommand(4)">上下往复 (Oscillate)</button>
                    <button class="btn-spiral" onclick="sendCommand(5)">螺旋上升 (Spiral)</button>
                    <button class="btn-eight" onclick="sendCommand(6)">8字飞行 (Figure-8)</button>
                </div>
                
                <div id="response"></div>
                
                <div class="info">
                    <p>API使用说明:</p>
                    <code>GET/POST /control?message=1/2/3/4/5/6/7/8</code><br>
                    1=起飞, 2=降落, 3=升高, 4=降低, 5=飞圈, 6=上下往复, 7=螺旋上升, 8=8字飞行
                </div>
            </div>
            
            <script>
                async function updateStatus() {
                    try {
                        const response = await fetch('/status');
                        const data = await response.json();
                        
                        document.getElementById('connection').textContent = 
                            data.connected ? '✓ 已连接' : '✗ 未连接';
                        document.getElementById('flying').textContent = 
                            data.flying ? '✓ 飞行中' : '○ 未飞行';
                    } catch (e) {
                        console.error('获取状态失败:', e);
                    }
                }
                
                async function getConfig() {
                    try {
                        const response = await fetch('/config');
                        const data = await response.json();
                        document.getElementById('drone-type').textContent = 
                            data.drone_type ? data.drone_type.toUpperCase() : 'UNKNOWN';
                    } catch (e) {
                        console.error('获取配置失败:', e);
                    }
                }
                
                async function sendCommand(message) {
                    const responseDiv = document.getElementById('response');
                    responseDiv.textContent = '发送中...';
                    responseDiv.className = 'response';
                    
                    try {
                        const response = await fetch(`/control?message=${message}`);
                        const data = await response.json();
                        
                        responseDiv.textContent = JSON.stringify(data, null, 2);
                        responseDiv.className = 'response ' + (data.success ? 'success' : 'error');
                        
                        setTimeout(updateStatus, 500);
                    } catch (e) {
                        responseDiv.textContent = '错误: ' + e.message;
                        responseDiv.className = 'response error';
                    }
                }
                
                getConfig();
                updateStatus();
                setInterval(updateStatus, 2000);
            </script>
        </body>
        </html>
        """
    
    def _get_fleet_mode_html(self):
        """集群模式的HTML界面"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>无人机控制系统 - 集群模式</title>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 1200px;
                    margin: 30px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 {
                    color: #333;
                    text-align: center;
                }
                .fleet-info {
                    background: #e3f2fd;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
                .control-panel {
                    display: grid;
                    grid-template-columns: 1fr 1fr 3fr;
                    gap: 10px;
                    align-items: center;
                    margin: 20px 0;
                }
                input, select, button {
                    padding: 10px;
                    font-size: 14px;
                    border-radius: 5px;
                }
                input, select {
                    border: 1px solid #ddd;
                }
                button {
                    border: none;
                    cursor: pointer;
                    transition: all 0.3s;
                    color: white;
                }
                .btn-takeoff { background: #4CAF50; }
                .btn-land { background: #f44336; }
                .btn-up { background: #2196F3; }
                .btn-down { background: #FF9800; }
                .btn-circle { background: #9C27B0; }
                .btn-oscillate { background: #00BCD4; }
                .btn-spiral { background: #E91E63; }
                .btn-eight { background: #3F51B5; }
                button:hover { opacity: 0.8; transform: scale(1.02); }
                .response {
                    margin-top: 15px;
                    padding: 10px;
                    border-radius: 5px;
                    font-family: monospace;
                    white-space: pre-wrap;
                    max-height: 400px;
                    overflow-y: auto;
                }
                .success { background: #c8e6c9; }
                .error { background: #ffcdd2; }
                .info {
                    text-align: center;
                    color: #666;
                    margin-top: 20px;
                    font-size: 14px;
                }
                label { font-weight: bold; margin-right: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚁 无人机控制系统 - 集群模式</h1>
                
                <div class="fleet-info">
                    <strong>集群信息:</strong><br>
                    <div id="fleet-status">加载中...</div>
                </div>
                
                <div class="control-panel">
                    <div>
                        <label>分组 (Group):</label>
                        <input type="text" id="group" placeholder="例: alpha" style="width: 100%">
                    </div>
                    <div>
                        <label>ID (可选):</label>
                        <input type="text" id="drone-id" placeholder="留空=全组" style="width: 100%">
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;">
                        <button class="btn-takeoff" onclick="sendCommand(1)">起飞</button>
                        <button class="btn-land" onclick="sendCommand(2)">降落</button>
                        <button class="btn-up" onclick="sendCommand(7)">升高</button>
                        <button class="btn-down" onclick="sendCommand(8)">降低</button>
                        <button class="btn-circle" onclick="sendCommand(3)">飞圈</button>
                        <button class="btn-oscillate" onclick="sendCommand(4)">往复</button>
                        <button class="btn-spiral" onclick="sendCommand(5)">螺旋</button>
                        <button class="btn-eight" onclick="sendCommand(6)">8字</button>
                    </div>
                </div>
                
                <div id="response"></div>
                
                <div class="info">
                    <p><strong>API使用说明 (集群模式):</strong></p>
                    <code>GET/POST /control?group=alpha&id=1&message=1</code><br>
                    <small>
                        • group: 必填，无人机分组名称（<strong>group=0 控制所有分组</strong>）<br>
                        • id: 可选，无人机编号（留空则控制整个分组）<br>
                        • message: 1=起飞, 2=降落, 3=升高, 4=降低<br>
                        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5=飞圈, 6=上下往复, 7=螺旋上升, 8=8字飞行
                    </small>
                </div>
            </div>
            
            <script>
                async function updateFleetStatus() {
                    try {
                        const response = await fetch('/fleet');
                        const data = await response.json();
                        
                        let html = `总计分组: ${data.total_groups}, 总计无人机: ${data.total_drones}<br><br>`;
                        
                        for (const [group, info] of Object.entries(data.groups)) {
                            html += `<strong>${group}</strong>: ${info.total_drones} 架 (`;
                            html += `连接: ${info.connected}, 飞行: ${info.flying}) `;
                            html += `[IDs: ${info.drone_ids.join(', ')}]<br>`;
                        }
                        
                        document.getElementById('fleet-status').innerHTML = html;
                    } catch (e) {
                        console.error('获取集群状态失败:', e);
                    }
                }
                
                async function sendCommand(message) {
                    const group = document.getElementById('group').value;
                    const droneId = document.getElementById('drone-id').value;
                    const responseDiv = document.getElementById('response');
                    
                    if (!group) {
                        responseDiv.textContent = '错误: 请输入分组名称 (group)';
                        responseDiv.className = 'response error';
                        return;
                    }
                    
                    responseDiv.textContent = '发送中...';
                    responseDiv.className = 'response';
                    
                    try {
                        let url = `/control?group=${group}&message=${message}`;
                        if (droneId) {
                            url += `&id=${droneId}`;
                        }
                        
                        const response = await fetch(url);
                        const data = await response.json();
                        
                        responseDiv.textContent = JSON.stringify(data, null, 2);
                        responseDiv.className = 'response ' + (data.success ? 'success' : 'error');
                        
                        setTimeout(updateFleetStatus, 500);
                    } catch (e) {
                        responseDiv.textContent = '错误: ' + e.message;
                        responseDiv.className = 'response error';
                    }
                }
                
                updateFleetStatus();
                setInterval(updateFleetStatus, 3000);
            </script>
        </body>
        </html>
        """
    
    async def handle_control(self, request):
        """处理控制请求"""
        # 获取参数（支持GET和POST）
        if request.method == 'GET':
            params = request.query
        else:  # POST
            try:
                params = await request.json()
            except:
                params = await request.post()
        
        message = params.get('message', '')
        
        if self.mode == "single":
            return await self._handle_single_mode_control(message)
        else:
            group = params.get('group', '')
            drone_id = params.get('id', '')
            return await self._handle_fleet_mode_control(message, group, drone_id)
    
    async def _handle_single_mode_control(self, message: str):
        """单机模式控制处理"""
        print(f"\n[单机模式] 收到控制指令: message={message}")
        
        try:
            if message == '1':
                result = await self.controller.takeoff(altitude=Config.DEFAULT_ALTITUDE)
            elif message == '2':
                result = await self.controller.land()
            elif message == '3':
                result = await self.controller.move_up(distance=Config.MOVE_STEP)
            elif message == '4':
                result = await self.controller.move_down(distance=Config.MOVE_STEP)
            elif message == '5':
                # 飞圈功能，只支持AirSim
                if hasattr(self.controller, 'fly_circle'):
                    result = await self.controller.fly_circle(diameter=5.0)
                else:
                    result = {
                        "success": False,
                        "message": "当前无人机类型不支持飞圈功能"
                    }
            elif message == '6':
                # 上下往复运动，只支持AirSim
                if hasattr(self.controller, 'vertical_oscillate'):
                    result = await self.controller.vertical_oscillate(distance=2.0, cycles=3)
                else:
                    result = {
                        "success": False,
                        "message": "当前无人机类型不支持上下往复运动功能"
                    }
            elif message == '7':
                # 螺旋上升，只支持AirSim
                if hasattr(self.controller, 'spiral_ascent'):
                    result = await self.controller.spiral_ascent(diameter=4.0, height=3.0)
                else:
                    result = {
                        "success": False,
                        "message": "当前无人机类型不支持螺旋上升功能"
                    }
            elif message == '8':
                # 8字飞行，只支持AirSim
                if hasattr(self.controller, 'figure_eight'):
                    result = await self.controller.figure_eight(size=3.0)
                else:
                    result = {
                        "success": False,
                        "message": "当前无人机类型不支持8字飞行功能"
                    }
            else:
                result = {
                    "success": False,
                    "message": f"无效的指令: {message}",
                    "help": "有效指令: 1=起飞, 2=降落, 3=升高, 4=降低, 5=飞圈, 6=上下往复, 7=螺旋上升, 8=8字飞行"
                }
            
            return web.json_response(result)
            
        except Exception as e:
            print(f"✗ 执行指令失败: {e}")
            return web.json_response({
                "success": False,
                "message": f"执行失败: {str(e)}"
            }, status=500)
    
    async def _handle_fleet_mode_control(self, message: str, group: str, drone_id: str):
        """集群模式控制处理"""
        # 特殊处理：group=0 表示所有分组
        if group == "0" or group == 0:
            target_info = "group=0 (所有分组)"
        else:
            target_info = f"group={group}"
            if drone_id:
                target_info += f", id={drone_id}"
            else:
                target_info += " (全组)"
        
        print(f"\n[集群模式] 收到控制指令: message={message}, {target_info}")
        
        try:
            # 检查group参数
            if not group:
                return web.json_response({
                    "success": False,
                    "message": "缺少必需参数: group",
                    "help": "集群模式需要指定分组: ?group=xxx&message=1 (group=0表示所有分组)"
                }, status=400)
            
            # 执行命令
            if message == '1':
                result = await self.fleet_manager.execute_command(
                    "takeoff", group, drone_id, altitude=Config.DEFAULT_ALTITUDE
                )
            elif message == '2':
                result = await self.fleet_manager.execute_command(
                    "land", group, drone_id
                )
            elif message == '7':
                result = await self.fleet_manager.execute_command(
                    "move_up", group, drone_id, distance=Config.MOVE_STEP
                )
            elif message == '8':
                result = await self.fleet_manager.execute_command(
                    "move_down", group, drone_id, distance=Config.MOVE_STEP
                )
            elif message == '3':
                result = await self.fleet_manager.execute_command(
                    "fly_circle", group, drone_id, diameter=5.0
                )
            elif message == '4':
                result = await self.fleet_manager.execute_command(
                    "vertical_oscillate", group, drone_id, distance=2.0, cycles=3
                )
            elif message == '5':
                result = await self.fleet_manager.execute_command(
                    "spiral_ascent", group, drone_id, diameter=4.0, height=3.0
                )
            elif message == '6':
                result = await self.fleet_manager.execute_command(
                    "figure_eight", group, drone_id, size=3.0
                )
            else:
                result = {
                    "success": False,
                    "message": f"无效的指令: {message}",
                    "help": "有效指令: 1=起飞, 2=降落, 7=升高, 8=降低, 3=飞圈, 4=上下往复, 5=螺旋上升, 6=8字飞行"
                }
            
            return web.json_response(result)
            
        except Exception as e:
            print(f"✗ 执行指令失败: {e}")
            return web.json_response({
                "success": False,
                "message": f"执行失败: {str(e)}"
            }, status=500)
    
    async def handle_status(self, request):
        """处理状态查询请求"""
        try:
            if self.mode == "single":
                status = await self.controller.get_status()
            else:
                # 集群模式：支持查询特定group/id或全部
                group = request.query.get('group', None)
                drone_id = request.query.get('id', None)
                status = await self.fleet_manager.get_status(group, drone_id)
            
            return web.json_response(status)
        except Exception as e:
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def handle_config(self, request):
        """处理配置查询请求"""
        return web.json_response(Config.get_config_info())
    
    async def handle_fleet_info(self, request):
        """处理集群信息查询（仅集群模式）"""
        if self.mode != "fleet":
            return web.json_response({
                "error": "此接口仅在集群模式下可用"
            }, status=400)
        
        try:
            info = self.fleet_manager.get_fleet_info()
            return web.json_response(info)
        except Exception as e:
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def start(self):
        """启动HTTP服务器"""
        # 初始化控制器
        await self.initialize()
        
        # 启动HTTP服务器
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        site = web.TCPSite(self.runner, Config.HTTP_HOST, Config.HTTP_PORT)
        await site.start()
        
        print(f"✓ HTTP服务器已启动: http://{Config.HTTP_HOST}:{Config.HTTP_PORT}")
        print(f"✓ 系统就绪，等待控制指令...\n")
        print("按 Ctrl+C 可安全退出（无人机将自动降落）\n")
        
        # 等待关闭信号
        await self.shutdown_event.wait()


async def main(mode: str, drone_type: str = None, fleet_config_file: str = None):
    """主函数"""
    # 设置配置
    Config.MODE = mode
    if drone_type:
        Config.DRONE_TYPE = drone_type
    if fleet_config_file:
        Config.FLEET_CONFIG_FILE = fleet_config_file
    
    # 打印配置
    Config.print_config()
    
    # 加载集群配置（如果是集群模式）
    fleet_config = {}
    if mode == "fleet":
        fleet_config = Config.load_fleet_config(fleet_config_file)
        if not fleet_config:
            print("✗ 无法加载集群配置，退出")
            return
    
    # 创建服务器
    server = DroneControlServer(
        mode=mode,
        drone_type=drone_type or Config.DRONE_TYPE,
        fleet_config=fleet_config
    )
    
    # 设置信号处理
    loop = asyncio.get_event_loop()
    
    def signal_handler(sig):
        print(f"\n\n收到中断信号 ({sig.name})，正在安全关闭...")
        server.shutdown_event.set()
    
    # 注册信号处理器
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    try:
        # 启动服务器
        await server.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        await server.cleanup()


if __name__ == "__main__":
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='无人机控制HTTP服务器')
    parser.add_argument(
        '--mode',
        choices=['single', 'fleet'],
        default='single',
        help='工作模式: single (单机) 或 fleet (集群)'
    )
    parser.add_argument(
        '--type',
        choices=['airsim', 'real'],
        help='无人机类型: airsim (模拟) 或 real (真实飞控) [仅单机模式]'
    )
    parser.add_argument(
        '--config',
        help='集群配置文件路径 [仅集群模式]'
    )
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='HTTP服务器监听地址 (默认: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='HTTP服务器端口 (默认: 8080)'
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if args.mode == "single" and not args.type:
        parser.error("单机模式需要指定 --type (airsim 或 real)")
    
    # 更新配置
    Config.HTTP_HOST = args.host
    Config.HTTP_PORT = args.port
    
    # 在Windows上，信号处理需要特殊处理
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        async def main_wrapper():
            server_mode = args.mode
            server_type = args.type
            fleet_config_file = args.config
            
            Config.MODE = server_mode
            if server_type:
                Config.DRONE_TYPE = server_type
            if fleet_config_file:
                Config.FLEET_CONFIG_FILE = fleet_config_file
            
            Config.print_config()
            
            fleet_config = {}
            if server_mode == "fleet":
                fleet_config = Config.load_fleet_config(fleet_config_file)
                if not fleet_config:
                    print("✗ 无法加载集群配置，退出")
                    return
            
            server = DroneControlServer(
                mode=server_mode,
                drone_type=server_type or Config.DRONE_TYPE,
                fleet_config=fleet_config
            )
            
            try:
                await server.start()
            except KeyboardInterrupt:
                print("\n\n收到中断信号，正在安全关闭...")
            finally:
                await server.cleanup()
        
        try:
            asyncio.run(main_wrapper())
        except KeyboardInterrupt:
            pass
    else:
        # Unix系统正常处理
        try:
            asyncio.run(main(args.mode, args.type, args.config))
        except KeyboardInterrupt:
            pass