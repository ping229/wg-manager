# WireGuard 分布式管理系统

一个功能完整的 WireGuard VPN 分布式管理系统，支持多节点管理、用户自助服务、流量控制等功能。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      中央管理服务器                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Portal    │  │    Admin    │  │      Database       │  │
│  │  用户门户   │  │  管理后台   │  │      (SQLite)       │  │
│  │  :8080      │  │  :8081      │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP API
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
  ┌───────────┐         ┌───────────┐         ┌───────────┐
  │   Agent   │         │   Agent   │         │   Agent   │
  │  节点 A   │         │  节点 B   │         │  节点 C   │
  │  :8082    │         │  :8082    │         │  :8082    │
  │  wg0      │         │  wg0      │         │  wg0      │
  └───────────┘         └───────────┘         └───────────┘
```

## 功能特性

### 用户门户 (Portal)
- 用户注册与登录
- 自动审批/人工审批流程
- VPN 配置文件生成与下载
- 二维码配置导入
- 多节点选择

### 管理后台 (Admin)
- 节点管理 (添加、编辑、删除、状态同步)
- 用户管理 (审批、禁用、删除)
- 管理员管理
- 操作审计日志
- 仪表盘统计

### 节点代理 (Agent)
- WireGuard 配置管理
- Peer 动态添加/删除
- 流量限速 (tc + nftables)
- 健康检查

## 快速部署

### 方式一：一键安装

```bash
# 下载项目
git clone https://github.com/your-repo/wg-manager.git
cd wg-manager

# 运行安装脚本
sudo bash install.sh
```

### 方式二：Docker 部署

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
vim .env

# 启动服务
docker-compose up -d
```

### 方式三：手动部署

```bash
# 1. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 构建前端
cd frontend/admin && npm install && npm run build
cd ../portal && npm install && npm run build
cd ../..

# 3. 配置环境变量
cp .env.example .env
vim .env

# 4. 初始化数据库
python -c "from backend.shared.database import init_db; init_db()"

# 5. 启动服务
venv/bin/uvicorn backend.portal.main:app --host 0.0.0.0 --port 8080 &
venv/bin/uvicorn backend.admin.main:app --host 127.0.0.1 --port 8081 &
```

## 部署模式

### 中央服务器模式
仅部署 Portal 和 Admin 服务，用于管理远程节点。

```bash
sudo bash install.sh --central
```

### 节点代理模式
仅部署 Agent 服务，在 VPN 节点上运行。

```bash
sudo bash install.sh --agent
```

### 单机模式
所有服务部署在同一台服务器上。

```bash
sudo bash install.sh
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SECRET_KEY | JWT 密钥 | 随机生成 |
| ENCRYPTION_KEY | 数据加密密钥 | 随机生成 |
| SUPER_ADMIN_PASSWORD | 超级管理员密码 | admin123 |
| DATABASE_URL | 数据库连接 | SQLite |

### 端口说明

| 端口 | 服务 | 访问 |
|------|------|------|
| 8080 | Portal | 公网访问 |
| 8081 | Admin | 内网访问 |
| 8082 | Agent | 内网访问 |
| 51820/udp | WireGuard | 公网访问 |

## 添加 VPN 节点

### 1. 在节点服务器上部署 Agent

```bash
# 复制项目到节点服务器
scp -r wg-manager root@node-ip:/opt/

# 运行节点部署脚本
cd /opt/wg-manager
sudo bash deploy.sh node-name wg0 51820 10.100.0.0/24
```

### 2. 在管理后台添加节点

1. 登录管理后台 `http://admin-ip:8081`
2. 进入「节点管理」
3. 点击「添加节点」
4. 填写节点信息：
   - 名称: 节点名称
   - 公网地址: 节点公网IP或域名
   - WG端口: 51820
   - 地址池: 10.100.0.0/24
   - Agent URL: http://节点IP:8082
   - API密钥: 部署时生成的密钥

## API 文档

启动服务后访问：
- Portal API: http://localhost:8080/docs
- Admin API: http://localhost:8081/docs
- Agent API: http://localhost:8082/docs

## 安全建议

1. 修改默认管理员密码
2. 使用 HTTPS (配置反向代理)
3. 限制 Admin 服务仅内网访问
4. 定期备份数据库
5. 定期更新密钥

## 目录结构

```
/opt/wg-manager/
├── backend/
│   ├── shared/          # 共享模块
│   │   ├── models.py    # 数据模型
│   │   ├── schemas.py   # Pydantic 模型
│   │   ├── database.py  # 数据库连接
│   │   ├── auth.py      # 认证模块
│   │   └── config.py    # 配置管理
│   ├── portal/          # 用户门户
│   ├── admin/           # 管理后台
│   └── agent/           # 节点代理
├── frontend/
│   ├── admin/           # 管理后台前端
│   └── portal/          # 用户门户前端
├── systemd/             # Systemd 服务文件
├── data/                # 数据目录
├── .env                 # 环境配置
├── requirements.txt     # Python 依赖
├── docker-compose.yml   # Docker 编排
├── Dockerfile           # Docker 镜像
├── install.sh           # 安装脚本
└── deploy.sh            # 节点部署脚本
```

## 许可证

MIT License
