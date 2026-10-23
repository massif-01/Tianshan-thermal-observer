# Tegrastats API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Release](https://img.shields.io/github/release/thomas-hiddenpeak/rm01OrinStatus.svg)](https://github.com/thomas-hiddenpeak/rm01OrinStatus/releases)

> 🚀 **高性能的NVIDIA Jetson系统监控API服务**  
> 提供实时系统状态监控、RESTful API接口和WebSocket数据流

专为NVIDIA Jetson设备设计的现代化系统监控解决方案，提供易于使用的API服务和实时数据推送。

## ⚡ 5分钟快速开始

```bash
# 克隆项目
git clone https://github.com/thomas-hiddenpeak/rm01OrinStatus.git
cd rm01OrinStatus

# 一键安装 (自动创建conda环境、安装依赖、配置服务)
./scripts/install.sh

# 验证安装
curl http://localhost:58090/api/health
```

� **[完整快速开始指南](docs/QUICKSTART.md)** → 5分钟完成部署  
📋 **[详细安装说明](docs/INSTALLATION_GUIDE.md)** → 深入了解安装选项

## ✨ 核心特性

| 功能 | 描述 |
|------|------|
| 🔍 **全面监控** | CPU、内存、GPU、功耗、温度全方位监控 |
| 🌐 **双重API** | REST API + WebSocket实时推送 (1Hz) |
| ⚙️ **生产就绪** | SystemD服务管理、自动重启、开机启动 |
| 🐍 **Python优先** | pip安装、CLI工具、编程接口 |
| 📱 **跨平台** | 支持Web、移动端、桌面应用开发 |

## 🛠️ 开发与贡献

### 运行测试
```bash
# WebSocket测试
python tests/test_simple_ws.py

# 完整测试套件
python -m pytest tests/
```

### 服务管理
```bash
# 启动/停止/重启
./scripts/manage_tegrastats.sh {start|stop|restart}

# 查看状态和日志
./scripts/manage_tegrastats.sh status
./scripts/manage_tegrastats.sh logs
```

## 📚 文档目录

| 文档 | 描述 |
|------|------|
| [🚀 快速开始](docs/QUICKSTART.md) | 5分钟完成部署 |
| [📋 安装指南](docs/INSTALLATION_GUIDE.md) | 详细安装步骤和配置 |
| [📖 API参考](docs/API_REFERENCE.md) | 完整API文档和示例 |
| [🛠️ 部署指南](docs/DEPLOYMENT_GUIDE.md) | 生产环境部署 |
| [📦 Wheel构建](docs/WHEEL_BUILD_GUIDE.md) | 包构建和分发指南 |
| [🤝 贡献指南](docs/CONTRIBUTING.md) | 参与项目开发 |

## 📖 使用示例

### REST API
```bash
# 健康检查
curl http://localhost:58090/api/health

# 获取系统状态  
curl http://localhost:58090/api/status | python -m json.tool
```

### WebSocket (JavaScript)
```javascript
const socket = io('http://localhost:58090');
socket.on('tegrastats_update', (data) => {
    console.log('实时数据:', data);
});
```

### Python客户端
```python
import requests
response = requests.get('http://localhost:58090/api/cpu')
print(response.json())
```

## 🌟 更多示例

📁 **[示例代码目录](examples/)** - 包含完整的客户端示例：
- Web dashboard示例
- Python监控脚本  
- JavaScript实时图表
- 系统告警脚本

## 🤝 社区与支持

- 🐛 [问题反馈](https://github.com/thomas-hiddenpeak/rm01OrinStatus/issues)
- 💡 [功能建议](https://github.com/thomas-hiddenpeak/rm01OrinStatus/discussions)
- 📧 联系维护者: thomashiddenpeak@gmail.com
- 📝 [更新日志](CHANGELOG.md)

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 详见 LICENSE 文件。

---

**⭐ 如果这个项目对您有帮助，请给个Star支持！**

Made with ❤️ for the NVIDIA Jetson community

## 📄 许可证

本项目采用 [MIT 许可证](LICENSE) - 详见 LICENSE 文件。

---

**⭐ 如果这个项目对您有帮助，请给个Star支持！**
