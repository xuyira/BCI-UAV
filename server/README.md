# BCI-UAV 无人机控制系统

一个基于HTTP的无人机控制系统，支持单机和多机集群模式，兼容AirSim模拟器和真实飞控（通过DroneKit/pymavlink）。

## 功能特性

- ✅ HTTP API接口控制无人机
- ✅ 支持AirSim模拟器
- ✅ 支持真实飞控（DroneKit/pymavlink）
- ✅ **单机模式**：控制单个无人机
- ✅ **集群模式**：管理多个无人机分组
- ✅ Web可视化控制界面
- ✅ 安全的中断处理（Ctrl+C自动降落）
- ✅ 异步操作，并行控制多架无人机

## 系统架构

```
server/
├── main.py                    # HTTP服务器主程序
├── drone_controller.py        # 无人机控制器抽象接口
├── airsim_controller.py       # AirSim实现
├── real_drone_controller.py   # 真实飞控实现
├── drone_fleet_manager.py     # 多无人机集群管理器
└── config.py                  # 配置管理
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**注意：**
- 如果只使用AirSim，只需安装 `aiohttp` 和 `airsim`
- 如果只使用真实飞控，只需安装 `aiohttp`、`dronekit` 和 `pymavlink`

---

## 单机模式 (Single Mode)

控制单个无人机。

### 启动服务器

#### 使用AirSim模拟器

```bash
cd server
python main.py --mode single --type airsim
```

#### 使用真实飞控

```bash
cd server
python main.py --mode single --type real
```

#### 自定义配置

```bash
python main.py --mode single --type airsim --host 0.0.0.0 --port 8080
```

### 访问控制界面

在浏览器中打开：`http://localhost:8080`

### API接口

**控制接口：** `GET/POST /control`

**参数：** `message=1/2/3/4`

- `message=1`: 起飞（Takeoff）
- `message=2`: 降落（Land）
- `message=3`: 升高（Move Up）
- `message=4`: 降低（Move Down）

**示例：**

```bash
# 起飞
curl "http://localhost:8080/control?message=1"

# 降落
curl "http://localhost:8080/control?message=2"
```

**响应格式：**

```json
{
  "success": true,
  "message": "起飞成功，高度: 5.0米"
}
```

---

## 集群模式 (Fleet Mode)

管理多个无人机分组，每个分组可以包含多架无人机。

### 1. 创建集群配置文件

复制示例配置文件：

```bash
cp fleet_config.example.json fleet_config.json
```

编辑 `fleet_config.json`：

```json
{
  "alpha": {
    "type": "airsim",
    "drones": [
      {"id": "1", "connection": "127.0.0.1:41451:Drone1"},
      {"id": "2", "connection": "127.0.0.1:41451:Drone2"},
      {"id": "3", "connection": "127.0.0.1:41451:Drone3"}
    ]
  },
  
  "bravo": {
    "type": "real",
    "drones": [
      {"id": "1", "connection": "udp:127.0.0.1:14550"},
      {"id": "2", "connection": "udp:127.0.0.1:14560"}
    ]
  }
}
```

**配置说明：**
- **分组名称**：可以自定义（如 `alpha`、`bravo`、`team1` 等）
- **type**：`airsim` 或 `real`
- **id**：无人机编号，在同一分组内唯一
- **connection**：
  - **AirSim格式**：`ip:port:vehicle_name`（例如 `127.0.0.1:41451:Drone1`）
    - ⚠️ **重要**：同一AirSim环境中的多架无人机使用**相同的ip:port**，通过**vehicle_name**区分
    - `vehicle_name` 必须与AirSim `settings.json` 中配置的 `VehicleName` 一致
  - **真实飞控格式**：`udp:ip:port`、`tcp:ip:port`、`/dev/ttyACM0`、`com3` 等

### 2. 配置AirSim多无人机环境（仅AirSim集群）

如果使用AirSim集群模式，需要先在AirSim的 `settings.json` 中配置多架无人机：

```json
{
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "Vehicles": {
    "Drone1": {
      "VehicleType": "SimpleFlight",
      "X": 0, "Y": 0, "Z": 0
    },
    "Drone2": {
      "VehicleType": "SimpleFlight",
      "X": 5, "Y": 0, "Z": 0
    },
    "Drone3": {
      "VehicleType": "SimpleFlight",
      "X": 10, "Y": 0, "Z": 0
    }
  }
}
```

**注意**：
- `settings.json` 中的 `VehicleName`（如 `Drone1`、`Drone2`）必须与 `fleet_config.json` 中的 `vehicle_name` 一致
- 设置不同的初始位置（X, Y, Z）避免无人机重叠
- AirSim的 `settings.json` 位置：
  - Windows: `%USERPROFILE%\Documents\AirSim\settings.json`
  - Linux: `~/Documents/AirSim/settings.json`

### 3. 启动集群服务器

```bash
cd server
python main.py --mode fleet --config config_dir/fleet_config.json
```

### 4. 访问集群控制界面

在浏览器中打开：`http://localhost:8080`

### API接口（集群模式）

**控制接口：** `GET/POST /control`

**参数：**
- `group`：必填，无人机分组名称
- `id`：可选，无人机编号（留空则控制整个分组）
- `message`：控制指令（1/2/3/4）

**示例：**

```bash
# 控制 alpha 分组的 1 号无人机起飞
curl "http://localhost:8080/control?group=alpha&id=1&message=1"

# 控制 alpha 分组的所有无人机起飞
curl "http://localhost:8080/control?group=alpha&message=1"

# 控制 bravo 分组的 2 号无人机降落
curl "http://localhost:8080/control?group=bravo&id=2&message=2"

# 控制 alpha 分组的所有无人机升高
curl "http://localhost:8080/control?group=alpha&message=3"
```

**响应格式（控制单个无人机）：**

```json
{
  "success": true,
  "message": "命令执行完成: ✓ 1 成功, ✗ 0 失败",
  "target": "group:alpha, id:1",
  "details": [
    {"success": true, "message": "起飞成功，高度: 5.0米"}
  ],
  "total": 1,
  "success_count": 1,
  "fail_count": 0
}
```

**响应格式（控制整个分组）：**

```json
{
  "success": true,
  "message": "命令执行完成: ✓ 3 成功, ✗ 0 失败",
  "target": "group:alpha (全部 3 架)",
  "details": [
    {"success": true, "message": "起飞成功，高度: 5.0米"},
    {"success": true, "message": "起飞成功，高度: 5.0米"},
    {"success": true, "message": "起飞成功，高度: 5.0米"}
  ],
  "total": 3,
  "success_count": 3,
  "fail_count": 0
}
```

### 其他API接口（集群模式）

**查询集群信息：**

```bash
curl "http://localhost:8080/fleet"
```

响应：

```json
{
  "total_groups": 2,
  "total_drones": 5,
  "groups": {
    "alpha": {
      "total_drones": 3,
      "drone_ids": ["1", "2", "3"],
      "connected": 3,
      "flying": 0
    },
    "bravo": {
      "total_drones": 2,
      "drone_ids": ["1", "2"],
      "connected": 2,
      "flying": 0
    }
  }
}
```

**查询特定分组状态：**

```bash
# 查询 alpha 分组的所有无人机状态
curl "http://localhost:8080/status?group=alpha"

# 查询 alpha 分组的 1 号无人机状态
curl "http://localhost:8080/status?group=alpha&id=1"
```

---

## 配置说明

可以通过环境变量或修改 `config.py` 来配置系统：

### 环境变量配置

```bash
# HTTP服务器配置
export HTTP_HOST=0.0.0.0
export HTTP_PORT=8080

# 工作模式 (single 或 fleet)
export MODE=single

# ===== 单机模式配置 =====
# 无人机类型 (airsim 或 real)
export DRONE_TYPE=airsim

# AirSim配置
export AIRSIM_IP=127.0.0.1
export AIRSIM_PORT=41451

# 真实飞控配置
export REAL_DRONE_CONNECTION=udp:127.0.0.1:14550

# ===== 集群模式配置 =====
# 集群配置文件路径
export FLEET_CONFIG_FILE=fleet_config.json

# ===== 飞行参数 =====
# 默认起飞高度（米）
export DEFAULT_ALTITUDE=5.0
# 升高/降低步长（米）
export MOVE_STEP=2.0
```

### 真实飞控连接字符串示例

```bash
# SITL模拟
udp:127.0.0.1:14550

# Linux串口
/dev/ttyACM0

# Windows串口
com3

# TCP连接
tcp:127.0.0.1:5760
```

---

## 使用场景

### 1. 单机开发测试

适用于开发和测试单个无人机控制算法。

```bash
python main.py --mode single --type airsim
```

### 2. 多机编队控制

适用于控制多架无人机进行编队飞行。

**场景示例**：控制3架无人机同时起飞

```bash
# 启动集群服务器
python main.py --mode fleet --config fleet_config.json

# 控制整个分组起飞
curl "http://localhost:8080/control?group=alpha&message=1"
```

### 3. 混合集群管理

同时管理AirSim模拟器和真实飞控。

```json
{
  "simulation": {
    "type": "airsim",
    "drones": [{"id": "1", "connection": "127.0.0.1:41451"}]
  },
  "real": {
    "type": "real",
    "drones": [{"id": "1", "connection": "udp:127.0.0.1:14550"}]
  }
}
```

### 4. BCI脑机接口集成

本系统可以与脑机接口（BCI）系统集成：

**单机模式集成示例：**

```python
import requests

# BCI识别到"起飞"意图
bci_command = 1  # 1=起飞

# 发送控制指令
response = requests.get(f"http://localhost:8080/control?message={bci_command}")
result = response.json()

if result['success']:
    print("无人机起飞成功！")
```

**集群模式集成示例：**

```python
import requests

# BCI识别到"alpha分组起飞"意图
group = "alpha"
command = 1  # 起飞

# 控制整个分组
response = requests.get(
    f"http://localhost:8080/control?group={group}&message={command}"
)
result = response.json()

print(f"成功: {result['success_count']}/{result['total']}")
```

---

## 安全特性

### 中断处理

程序实现了安全的中断处理机制：

1. 按 `Ctrl+C` 时，程序不会立即退出
2. 系统会检查所有无人机是否在飞行
3. 如果在飞行，会自动执行紧急降落
4. 所有无人机降落完成后才会断开连接并退出

**这确保了无人机不会因为程序意外退出而失控！**

### 集群模式的并行控制

集群模式下，控制指令会并行发送到多架无人机，提高响应速度。同时，系统会汇总所有无人机的执行结果，便于监控。

---

## 开发指南

### 添加新的控制命令

1. 在 `DroneController` 基类中添加抽象方法
2. 在 `AirSimController` 和 `RealDroneController` 中实现该方法
3. 在 `main.py` 的控制处理函数中添加新的消息处理

### 自定义飞行参数

修改 `config.py` 中的默认参数：

```python
DEFAULT_ALTITUDE = 5.0  # 默认起飞高度
MOVE_STEP = 2.0         # 升降步长
```

---

## 故障排除

### 无法连接到AirSim

1. 确认AirSim已启动
2. 检查AirSim是否配置为多旋翼模式
3. 验证IP和端口配置正确

### 无法连接到真实飞控

1. 检查连接字符串是否正确
2. 确认飞控已通电并连接
3. 检查串口/UDP端口权限
4. 查看飞控是否支持MAVLink协议

### 集群模式无法启动

1. 检查 `fleet_config.json` 文件格式是否正确
2. 验证所有无人机的连接信息
3. 确保各无人机的端口不冲突

### 无人机不响应控制指令

1. 检查 `/status` 接口确认连接状态
2. 确认无人机已正确初始化
3. 查看服务器日志输出
4. 对于真实飞控，检查GPS状态和飞行模式

---

## 命令行参数参考

```
python main.py [options]

选项:
  --mode {single,fleet}   工作模式 (默认: single)
  --type {airsim,real}    无人机类型 [仅单机模式]
  --config FILE           集群配置文件路径 [仅集群模式]
  --host HOST             HTTP服务器监听地址 (默认: 0.0.0.0)
  --port PORT             HTTP服务器端口 (默认: 8080)
```

**示例：**

```bash
# 单机模式 - AirSim
python main.py --mode single --type airsim

# 单机模式 - 真实飞控
python main.py --mode single --type real

# 集群模式
python main.py --mode fleet --config fleet_config.json

# 自定义端口
python main.py --mode single --type airsim --port 9090
```

---

## 注意事项

⚠️ **重要安全提示：**

1. 首次使用请在模拟环境（AirSim）中测试
2. 使用真实飞控时，确保在安全的测试环境中
3. 集群模式下，确保所有无人机之间有足够的安全距离
4. 保持对所有无人机的视线观察
5. 确保电池电量充足
6. 遵守当地的无人机飞行法规
7. 随时准备使用遥控器接管控制
8. 在室外飞行前，务必在室内或模拟环境中充分测试

---

## 许可证

本项目基于您的需求开发，请根据实际情况添加合适的许可证。

## 联系方式

如有问题或建议，请通过项目Issues反馈。