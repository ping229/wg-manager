# WireGuard 管理系统使用手册

## 系统架构

```
┌──────────────────────────────────────┐
│          中央管理服务器               │
│  ┌─────────────┐  ┌─────────────┐    │
│  │   Portal    │  │    Admin    │    │
│  │  用户门户   │  │  管理后台   │    │
│  │  :8080      │  │  :8081      │    │
│  └─────────────┘  └─────────────┘    │
└──────────────────────────────────────┘
                 │
                 │ HTTP API 调用
                 ▼
┌──────────────────────────────────────┐
│           VPN节点服务器               │
│  ┌─────────────┐  ┌─────────────┐    │
│  │   Agent     │  │  WireGuard  │    │
│  │  节点代理   │  │  VPN服务    │    │
│  │  :8082      │  │  :51820/udp │    │
│  └─────────────┘  └─────────────┘    │
└──────────────────────────────────────┘
```

## 一、添加VPN节点

### 1.1 准备VPN节点服务器

需要一台独立的服务器作为VPN节点，要求：
- 公网IP可访问
- 开放端口：8082(TCP)、51820(UDP)
- 已安装 Python 3.10+

### 1.2 在VPN节点上部署Agent

**步骤1：复制项目到节点服务器**

```bash
# 在中央服务器上执行
scp -r /opt/wg-manager root@节点IP:/opt/
```

**步骤2：在节点服务器上安装**

```bash
# SSH登录到VPN节点服务器
ssh root@节点IP

# 运行安装脚本（仅安装Agent模式）
cd /opt/wg-manager
bash install.sh --agent --skip-frontend
```

**步骤3：配置WireGuard**

```bash
# 生成密钥对
wg genkey | tee /etc/wireguard/privatekey | wg pubkey > /etc/wireguard/publickey
chmod 600 /etc/wireguard/privatekey

# 查看公钥
cat /etc/wireguard/publickey

# 创建配置文件
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/privatekey)
Address = 10.100.0.1/24
ListenPort = 51820

# 此节点由WireGuard Manager管理
EOF

# 启动WireGuard
wg-quick up wg0
systemctl enable wg-quick@wg0
```

**步骤4：启动Agent服务**

```bash
systemctl start wg-agent
systemctl enable wg-agent
```

### 1.3 在管理后台添加节点

登录管理后台 → 节点管理 → 添加节点

| 字段 | 说明 | 示例 |
|------|------|------|
| 名称 | 节点标识名 | `上海节点` |
| 公网地址 | 节点公网IP或域名 | `vpn-sh.example.com` 或 `1.2.3.4` |
| WG端口 | WireGuard监听端口 | `51820` |
| 接口名 | WireGuard接口名 | `wg0` |
| 地址池 | VPN客户端IP范围 | `10.100.0.0/24` |
| DNS | 客户端使用的DNS | `8.8.8.8` |
| MTU | 最大传输单元 | `1420` |
| Keepalive | 心跳间隔(秒) | `25` |
| Agent URL | Agent API地址 | `http://节点IP:8082` |
| API密钥 | 认证密钥 | 见下方 |

**查看API密钥：**
```bash
grep ENCRYPTION_KEY /opt/wg-manager/.env
```

## 二、用户注册流程

### 2.1 用户注册

1. 用户访问 Portal (端口8080)
2. 点击「注册」填写用户名、密码、邮箱
3. 等待管理员审批

### 2.2 管理员审批

1. 登录 Admin (端口8081)
2. 进入「注册审批」
3. 审核用户信息，选择「通过」或「拒绝」

### 2.3 用户获取配置

审批通过后，用户：
1. 登录 Portal
2. 选择节点，申请VPN配置
3. 下载配置文件或扫描二维码

## 三、客户端配置

### 3.1 下载客户端

| 平台 | 下载地址 |
|------|----------|
| Windows | https://www.wireguard.com/install/ |
| macOS | App Store 搜索 WireGuard |
| iOS | App Store 搜索 WireGuard |
| Android | Play Store 搜索 WireGuard |

### 3.2 导入配置

**方式一：文件导入**
1. 下载 .conf 配置文件
2. 打开 WireGuard 客户端
3. 选择「从文件导入隧道」

**方式二：二维码导入（移动端）**
1. 打开 WireGuard 手机客户端
2. 点击右上角扫描图标
3. 扫描 Portal 页面的二维码

## 四、管理功能

### 4.1 节点管理

- **同步**：检查节点Agent是否在线
- **禁用**：清空该节点所有Peer，停止服务
- **启用**：恢复节点服务

### 4.2 用户管理

- 查看用户列表
- 禁用/启用用户
- 修改用户信息
- 删除用户

### 4.3 管理员管理

- 超级管理员可添加/删除管理员
- 修改管理员密码

### 4.4 操作日志

- 记录所有管理操作
- 支持按类型、时间筛选

## 五、常见问题

### Q1: 用户无法连接VPN？

检查：
1. 节点防火墙是否开放 51820/UDP
2. 节点 WireGuard 是否运行：`wg show`
3. 客户端配置是否正确

### Q2: Agent 连接失败？

检查：
1. Agent服务是否运行：`systemctl status wg-agent`
2. 防火墙是否开放 8082/TCP
3. API密钥是否一致

### Q3: 如何修改管理员密码？

登录后进入「管理员」页面，点击「修改密码」

### Q4: 如何备份？

```bash
# 备份数据库
cp /opt/wg-manager/data/wg.db /backup/wg_$(date +%Y%m%d).db

# 备份配置
cp /opt/wg-manager/.env /backup/
```

## 六、服务管理命令

```bash
# 查看服务状态
systemctl status wg-portal wg-admin wg-agent

# 重启服务
systemctl restart wg-portal wg-admin wg-agent

# 查看日志
journalctl -u wg-portal -f
journalctl -u wg-admin -f
journalctl -u wg-agent -f

# 查看WireGuard状态
wg show
```

## 七、安全建议

1. **修改默认密码**：首次登录后立即修改
2. **使用HTTPS**：配置反向代理（Nginx/Caddy）
3. **限制访问**：Admin后台限制内网访问
4. **定期备份**：备份数据库和配置文件
5. **更新密钥**：定期更换JWT和加密密钥
