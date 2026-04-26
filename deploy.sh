#!/bin/bash
#
# WireGuard 节点部署脚本
# 用于在 VPN 节点上部署 Agent 服务
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 配置
INSTALL_DIR="/opt/wg-manager"
NODE_NAME="${1:-wg-node}"
WG_INTERFACE="${2:-wg0}"
WG_PORT="${3:-51820}"
ADDRESS_POOL="${4:-10.100.0.0/24}"
API_KEY="${5:-$(openssl rand -hex 16)}"

# 检查 root
if [[ $EUID -ne 0 ]]; then
    log_error "需要 root 权限"
    exit 1
fi

# 安装 WireGuard
log_info "安装 WireGuard..."
if command -v apt-get &> /dev/null; then
    apt-get update
    apt-get install -y wireguard-tools iptables ipset
elif command -v yum &> /dev/null; then
    yum install -y wireguard-tools iptables ipset
fi

# 创建目录
mkdir -p /etc/wireguard
chmod 700 /etc/wireguard

# 生成密钥对
log_info "生成 WireGuard 密钥对..."
cd /etc/wireguard
wg genkey | tee privatekey | wg pubkey > publickey
chmod 600 privatekey

PRIVATE_KEY=$(cat privatekey)
PUBLIC_KEY=$(cat publickey)

# 创建 WireGuard 配置
log_info "创建 WireGuard 配置..."
cat > /etc/wireguard/${WG_INTERFACE}.conf << EOF
[Interface]
PrivateKey = ${PRIVATE_KEY}
Address = ${ADDRESS_POOL%%/*}.1/${ADDRESS_POOL#*/}
ListenPort = ${WG_PORT}
SaveConfig = false

# WireGuard Manager Agent Node
# Managed by: ${NODE_NAME}
EOF

chmod 600 /etc/wireguard/${WG_INTERFACE}.conf

# 配置系统参数
log_info "配置系统参数..."
cat >> /etc/sysctl.conf << EOF

# WireGuard 优化
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
EOF
sysctl -p

# 启动 WireGuard
log_info "启动 WireGuard..."
wg-quick up ${WG_INTERFACE}
systemctl enable wg-quick@${WG_INTERFACE}

# 安装 Agent 服务
log_info "安装 Agent 服务..."
cd $INSTALL_DIR

if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    deactivate
fi

# 配置环境变量
cat >> $INSTALL_DIR/.env << EOF

# Agent 配置
WG_INTERFACE=${WG_INTERFACE}
WG_PORT=${WG_PORT}
EOF

# 安装并启动服务
cp $INSTALL_DIR/systemd/wg-agent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable wg-agent
systemctl start wg-agent

# 显示结果
echo ""
echo "=========================================="
echo "  WireGuard 节点部署完成!"
echo "=========================================="
echo ""
echo "节点名称: $NODE_NAME"
echo "WireGuard 接口: $WG_INTERFACE"
echo "监听端口: $WG_PORT"
echo "地址池: $ADDRESS_POOL"
echo ""
echo "公钥: $PUBLIC_KEY"
echo ""
echo "Agent API: http://<本机IP>:8082"
echo "API 密钥: $API_KEY"
echo ""
echo "请在中央管理后台添加此节点:"
echo "  节点名称: $NODE_NAME"
echo "  公网地址: <公网IP或域名>"
echo "  WG端口: $WG_PORT"
echo "  地址池: $ADDRESS_POOL"
echo "  公钥: $PUBLIC_KEY"
echo "  Agent URL: http://<本机IP>:8082"
echo "  API密钥: $API_KEY"
echo ""
echo "=========================================="
