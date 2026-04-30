# WireGuard 分布式管理系统

[![Version](https://img.shields.io/badge/version-1.0.0-green.svg)](https://github.com/ping229/wg-manager)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

一个功能完整的 WireGuard VPN 分布式管理系统，支持多节点管理、用户自助服务、流量控制等功能。

## 版本信息

**v1.0.0** - 首个正式发布版本

### 主要功能

- ✅ **用户门户 (Portal)**：用户注册、登录、VPN 配置自动生成与下载
- ✅ **管理后台 (Admin)**：节点管理、用户管理、批量操作、导入导出
- ✅ **节点代理 (Agent)**：WireGuard 配置管理、Peer 动态管理、流量限速
- ✅ **统一 KEY 认证**：Portal-Admin、Agent-Admin 间统一 KEY 认证机制
- ✅ **命令行工具**：KEY 管理和查看命令
- ✅ **一键安装**：支持 Portal、Admin、Agent 独立部署和单机部署

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        典型分布式部署                             │
│                                                                 │
│  ┌─────────────────────┐         ┌─────────────────────┐       │
│  │      Portal         │         │       Admin         │       │
│  │    用户门户服务器    │◄───────►│    管理后台服务器    │       │
│  │      :8080          │  KEY    │       :8081         │       │
│  │                     │         │    Database(SQLite) │       │
│  └─────────────────────┘         └─────────────────────┘       │
│                                           │                     │
│                                           │ HTTP API (KEY)      │
│                                           │                     │
│                    ┌──────────────────────┼────────────────┐    │
│                    │                      │                │    │
│                    ▼                      ▼                ▼    │
│              ┌───────────┐          ┌───────────┐    ┌───────────┐
│              │   Agent   │          │   Agent   │    │   Agent   │
│              │  节点 A   │          │  节点 B   │    │  节点 C   │
│              │  :8082    │          │  :8082    │    │  :8082    │
│              │  wg0      │          │  wg0      │    │  wg0      │
│              └───────────┘          └───────────┘    └───────────┘
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 方式一：单机部署（推荐测试使用）

所有服务部署在一台服务器上，适合测试环境或小型部署。

```bash
# 下载项目
git clone https://github.com/ping229/wg-manager.git
cd wg-manager

# 一键安装
sudo bash install.sh
```

安装完成后：
- Portal: http://服务器IP:8080
- Admin: http://服务器IP:8081 (默认账号: admin / admin123)

### 方式二：分布式部署（推荐生产使用）

将 Portal、Admin、Agent 分别部署在不同服务器上。

#### 1. 部署 Admin（管理后台）

```bash
# 在 Admin 服务器上
git clone https://github.com/ping229/wg-manager.git
cd wg-manager
sudo bash install.sh --admin
```

#### 2. 部署 Portal（用户门户）

```bash
# 在 Portal 服务器上
git clone https://github.com/ping229/wg-manager.git
cd wg-manager
sudo bash install.sh --portal
```

配置 Portal 连接 Admin：
```bash
# 编辑 /opt/wg-manager/.env
ADMIN_URL=http://admin服务器IP:8081
KEY=与Admin端配置相同
```

#### 3. 部署 Agent（VPN 节点）

```bash
# 在节点服务器上
git clone https://github.com/ping229/wg-manager.git
cd wg-manager
sudo bash install.sh --agent
```

安装完成后会显示 WireGuard 公钥，需要在 Admin 后台配置。

## 分布式部署详细配置

### 认证机制说明

系统使用统一 KEY 进行双向认证：

| 连接类型 | 认证方式 | 配置位置 |
|---------|---------|---------|
| Portal → Admin | KEY | Portal .env 的 KEY = Admin Portal站点管理的 KEY |
| Admin → Agent | KEY | Admin 节点管理的 KEY = Agent .env 的 KEY |

### 配置示例

#### Portal 配置 (`/opt/wg-manager/.env`)

```bash
# Portal 服务配置
PORTAL_HOST=0.0.0.0
PORTAL_PORT=8080

# Admin 连接配置
ADMIN_URL=http://admin服务器IP:8081
KEY=your-portal-key-here

# 数据加密密钥
ENCRYPTION_KEY=your-encryption-key-32bytes

# JWT 密钥
SECRET_KEY=your-jwt-secret-key
```

#### Admin 配置 (`/opt/wg-manager/.env`)

```bash
# Admin 服务配置
ADMIN_HOST=0.0.0.0
ADMIN_PORT=8081

# 数据库
DATABASE_URL=sqlite:////opt/wg-manager/data/admin.db

# 加密密钥
SECRET_KEY=your-jwt-secret-key
ENCRYPTION_KEY=your-encryption-key-32bytes

# 超级管理员密码
SUPER_ADMIN_PASSWORD=admin123
```

#### Agent 配置 (`/opt/wg-manager/.env`)

```bash
# Agent 服务配置
AGENT_HOST=0.0.0.0
AGENT_PORT=8082

# 认证 KEY（必须与 Admin 端节点配置的 KEY 相同）
KEY=your-agent-key-here
```

### 添加 VPN 节点

#### 1. 在节点服务器上部署 Agent

```bash
sudo bash install.sh --agent
```

安装完成后记录显示的 **WireGuard 公钥**。

#### 2. 在 Admin 后台添加节点

1. 登录 Admin: `http://admin-ip:8081`
2. 进入「节点管理」→「添加节点」
3. 填写信息：
   - **名称**：节点名称（如：北京节点）
   - **公网地址**：节点公网 IP 或域名
   - **WG端口**：51820（默认）
   - **地址池**：10.100.0.0/24（每个节点使用不同地址池）
   - **Agent URL**：http://节点IP:8082
   - **KEY**：与 Agent 端 .env 中的 KEY 相同
4. 保存后节点显示「在线」即配置成功

### 添加 Portal 站点

如果部署了多个 Portal，需要在 Admin 后台注册：

1. 进入「Portal 站点管理」→「添加站点」
2. 填写信息：
   - **名称**：站点名称
   - **地址**：Portal 访问地址
   - **KEY**：与 Portal 端 .env 中的 KEY 相同

## 功能说明

### 用户门户 (Portal)

- 用户注册与登录
- 自动审批/人工审批流程
- VPN 配置文件生成与下载
- 二维码配置导入
- 多节点选择

### 管理后台 (Admin)

- **节点管理**
  - 添加、编辑、删除节点
  - 批量启用/禁用/删除
  - 导入/导出节点配置
  - 节点在线状态监控
  - 访问控制（禁止特定用户访问）

- **用户管理**
  - 审批/拒绝注册申请
  - 禁用/启用用户
  - 重置用户配置

- **Portal 站点管理**
  - 添加/编辑/删除 Portal 站点
  - 站点连接测试

- **仪表盘**
  - 节点统计
  - 用户统计
  - 操作日志

### 节点代理 (Agent)

- WireGuard 自动配置
- Peer 动态添加/删除
- 流量限速 (tc + nftables)
- 健康检查接口

## 命令行工具

### 查看 KEY

```bash
cd /opt/wg-manager
venv/bin/python -m backend.cli --show-key
```

### 重新生成 KEY

```bash
cd /opt/wg-manager
venv/bin/python -m backend.cli --regenerate-key
```

生成新 KEY 后需要：
1. 更新 Portal/Agent 端的 .env 配置
2. 在 Admin 后台更新对应的站点/节点 KEY
3. 重启相关服务

## 端口说明

| 端口 | 服务 | 访问范围 | 说明 |
|------|------|---------|------|
| 8080 | Portal | 公网 | 用户门户 |
| 8081 | Admin | 内网 | 管理后台 |
| 8082 | Agent | 内网 | 节点代理 API |
| 51820/udp | WireGuard | 公网 | VPN 端口 |

## 安全建议

1. ✅ 修改默认管理员密码
2. ✅ Admin 服务仅允许内网访问
3. ✅ 使用 HTTPS（配置 Nginx 反向代理）
4. ✅ 定期备份数据库
5. ✅ 定期更新 KEY

## 常见问题

### Q: Agent 显示离线？

1. 检查 Agent 服务状态：`systemctl status wg-agent`
2. 检查网络连通性：`curl http://agent-ip:8082/health`
3. 检查 KEY 是否匹配

### Q: VPN 连接后无法上网？

1. 检查 WireGuard 状态：`wg show`
2. 检查 NAT 规则：`iptables -t nat -L POSTROUTING -n -v`
3. 确认 IP 转发开启：`cat /proc/sys/net/ipv4/ip_forward`
4. 确认地址池与 Admin 配置一致

### Q: 如何重置管理员密码？

```bash
cd /opt/wg-manager
source venv/bin/activate
python -c "
from backend.admin.database import SessionLocal
from backend.admin.models import AdminUser
from backend.shared.auth import get_password_hash
db = SessionLocal()
admin = db.query(AdminUser).filter(AdminUser.username == 'admin').first()
admin.password_hash = get_password_hash('new_password')
db.commit()
print('Password updated')
"
```

## 更新日志

### v1.0.0 (2026-04-30)

**新增功能**
- 用户门户：注册、登录、VPN 配置管理
- 管理后台：节点管理、用户管理、批量操作、导入导出
- 节点代理：WireGuard 自动配置、流量控制
- 统一 KEY 认证机制
- 命令行管理工具
- 一键安装脚本

**已知限制**
- 仅支持 SQLite 数据库
- 流量控制需要 Linux 内核支持

## 目录结构

```
/opt/wg-manager/
├── backend/
│   ├── shared/          # 共享模块
│   │   ├── schemas.py   # Pydantic 模型
│   │   ├── auth.py      # 认证模块
│   │   └── config.py    # Agent 配置
│   ├── portal/          # 用户门户
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── routes/
│   ├── admin/           # 管理后台
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── routes/
│   └── agent/           # 节点代理
│       ├── main.py
│       ├── routes/
│       └── services/
├── frontend/
│   ├── admin/           # 管理后台前端 (Vue3 + Element Plus)
│   └── portal/          # 用户门户前端 (Vue3 + Element Plus)
├── systemd/             # Systemd 服务文件
├── data/                # 数据目录
│   ├── portal.db        # Portal 数据库
│   ├── admin.db         # Admin 数据库
│   ├── logs/            # 日志目录
│   └── configs/         # 配置目录
├── .env                 # 环境配置
├── requirements.txt     # Python 依赖
├── install.sh           # 安装脚本
└── README.md
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request。
