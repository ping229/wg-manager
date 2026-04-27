#!/bin/bash
#
# WireGuard 分布式管理系统安装脚本
# 用法: sudo bash install.sh [选项]
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 默认配置
INSTALL_DIR="/opt/wg-manager"
PYTHON_CMD="python3"
PIP_CMD="pip3"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为 root 用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要 root 权限运行"
        exit 1
    fi
}

# 检查系统依赖
check_dependencies() {
    log_info "检查系统依赖..."

    local missing=()

    # 检查 Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        missing+=("python3")
    fi

    # 检查 pip
    if ! command -v $PIP_CMD &> /dev/null; then
        missing+=("python3-pip")
    fi

    # 检查 WireGuard (仅 agent 和 all 模式需要)
    if [[ $DEPLOY_MODE == "agent" || $DEPLOY_MODE == "all" ]]; then
        if ! command -v wg &> /dev/null; then
            missing+=("wireguard-tools")
        fi
    fi

    # 检查 Node.js (用于前端构建)
    if ! command -v node &> /dev/null; then
        log_warn "Node.js 未安装，将跳过前端构建"
        SKIP_FRONTEND=1
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warn "缺少依赖: ${missing[*]}"
        log_info "尝试安装缺失的依赖..."

        if command -v apt-get &> /dev/null; then
            apt-get update
            apt-get install -y ${missing[@]}
        elif command -v yum &> /dev/null; then
            yum install -y ${missing[@]}
        else
            log_error "无法自动安装依赖，请手动安装: ${missing[*]}"
            exit 1
        fi
    fi

    log_info "依赖检查完成"
}

# 安装 Python 依赖
install_python_deps() {
    log_info "安装 Python 依赖..."

    # 确保安装目录存在
    if [[ ! -d "$INSTALL_DIR" ]]; then
        # 检查当前目录是否包含项目文件
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [[ -f "$script_dir/requirements.txt" && "$script_dir" != "$INSTALL_DIR" ]]; then
            log_info "复制项目文件到 $INSTALL_DIR ..."
            mkdir -p "$INSTALL_DIR"
            cp -r "$script_dir"/* "$INSTALL_DIR/"
        else
            log_error "安装目录不存在且无法找到项目文件: $INSTALL_DIR"
            exit 1
        fi
    fi

    cd $INSTALL_DIR

    # 创建虚拟环境
    if [[ ! -d "venv" ]]; then
        $PYTHON_CMD -m venv venv
    fi

    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate

    log_info "Python 依赖安装完成"
}

# 构建前端
build_frontend() {
    if [[ $SKIP_FRONTEND -eq 1 ]]; then
        log_warn "跳过前端构建 (Node.js 未安装)"
        return
    fi

    log_info "构建前端..."

    # 根据部署模式构建对应前端
    if [[ $DEPLOY_MODE == "portal" || $DEPLOY_MODE == "all" ]]; then
        cd $INSTALL_DIR/frontend/portal
        if [[ ! -d "node_modules" ]]; then
            npm install
        fi
        npm run build
        log_info "Portal 前端构建完成"
    fi

    if [[ $DEPLOY_MODE == "admin" || $DEPLOY_MODE == "all" ]]; then
        cd $INSTALL_DIR/frontend/admin
        if [[ ! -d "node_modules" ]]; then
            npm install
        fi
        npm run build
        log_info "Admin 前端构建完成"
    fi

    cd $INSTALL_DIR
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."

    mkdir -p $INSTALL_DIR/data
    mkdir -p $INSTALL_DIR/data/logs
    mkdir -p $INSTALL_DIR/data/configs

    # WireGuard 配置目录 (仅 agent 和 all 模式)
    if [[ $DEPLOY_MODE == "agent" || $DEPLOY_MODE == "all" ]]; then
        mkdir -p /etc/wireguard
        chmod 700 /etc/wireguard
    fi

    chmod 700 $INSTALL_DIR/data
}

# 生成配置文件
generate_config() {
    log_info "生成配置文件..."

    local env_file="$INSTALL_DIR/.env"

    if [[ -f "$env_file" ]]; then
        log_warn ".env 文件已存在，跳过生成"
        return
    fi

    # 生成随机密钥
    local secret_key=$(openssl rand -hex 32)
    local encryption_key=$(openssl rand -hex 16)
    local portal_api_key=$(openssl rand -hex 16)

    cat > "$env_file" << EOF
# WireGuard 管理系统配置文件
# 生成时间: $(date)
# 部署模式: $DEPLOY_MODE

# JWT 密钥 (Portal 和 Admin 独立，无需相同)
SECRET_KEY=${secret_key}

# 数据加密密钥 (32字节)
ENCRYPTION_KEY=${encryption_key}

# Portal 名称 (仅 Portal 模式需要)
PORTAL_NAME=WireGuard Portal

# Portal API 密钥 (供 Admin 回调使用)
PORTAL_API_KEY=${portal_api_key}

# 超级管理员初始密码 (仅 Admin 使用，首次启动后请修改)
SUPER_ADMIN_PASSWORD=admin123

# Portal 服务配置
PORTAL_HOST=0.0.0.0
PORTAL_PORT=8080

# Admin 服务配置
ADMIN_HOST=127.0.0.1
ADMIN_PORT=8081

# 数据库路径
DATABASE_URL=sqlite:///${INSTALL_DIR}/data/portal.db

# Agent 服务配置
AGENT_HOST=127.0.0.1
AGENT_PORT=8082
DEFAULT_AGENT_URL=http://127.0.0.1:8082
AGENT_API_KEY=
EOF

    chmod 600 "$env_file"
    log_info "配置文件已生成: $env_file"

    if [[ $DEPLOY_MODE == "portal" ]]; then
        log_info ""
        log_info "Portal 部署完成后的接入步骤："
        log_info "  1. 访问 Portal 首页"
        log_info "  2. 在页面下方填写 Admin 的 URL 和 API 密钥"
        log_info "  3. 点击'申请接入'按钮"
        log_info "  4. 等待 Admin 审核通过"
        log_info ""
    elif [[ $DEPLOY_MODE == "admin" ]]; then
        log_info ""
        log_info "Admin 部署完成后的操作："
        log_info "  1. 访问 Admin 后台 (默认账号: admin / admin123)"
        log_info "  2. 在'Portal接入管理'中审核 Portal 的接入申请"
        log_info "  3. 审核通过后 Portal 即可正常使用"
        log_info ""
    fi
}

# 安装 systemd 服务
install_systemd_services() {
    log_info "安装 systemd 服务..."

    local systemd_dir="/etc/systemd/system"

    case $DEPLOY_MODE in
        portal)
            cp $INSTALL_DIR/systemd/wg-portal.service $systemd_dir/
            systemctl daemon-reload
            systemctl enable wg-portal
            log_info "已安装服务: wg-portal"
            ;;
        admin)
            cp $INSTALL_DIR/systemd/wg-admin.service $systemd_dir/
            systemctl daemon-reload
            systemctl enable wg-admin
            log_info "已安装服务: wg-admin"
            ;;
        agent)
            cp $INSTALL_DIR/systemd/wg-agent.service $systemd_dir/
            systemctl daemon-reload
            systemctl enable wg-agent
            log_info "已安装服务: wg-agent"
            ;;
        all)
            cp $INSTALL_DIR/systemd/wg-portal.service $systemd_dir/
            cp $INSTALL_DIR/systemd/wg-admin.service $systemd_dir/
            cp $INSTALL_DIR/systemd/wg-agent.service $systemd_dir/
            systemctl daemon-reload
            systemctl enable wg-portal wg-admin wg-agent
            log_info "已安装服务: wg-portal, wg-admin, wg-agent"
            ;;
    esac
}

# 初始化数据库
init_database() {
    # 仅 portal、admin、all 模式需要初始化数据库
    if [[ $DEPLOY_MODE == "agent" ]]; then
        log_info "Agent 模式不需要初始化数据库，跳过"
        return
    fi

    log_info "初始化数据库..."

    cd $INSTALL_DIR
    source venv/bin/activate

    $PYTHON_CMD << 'EOF'
from backend.shared.database import init_db, engine
from backend.shared.models import Base

# 创建所有表
Base.metadata.create_all(bind=engine)
print("Database initialized successfully")
EOF

    deactivate
    log_info "数据库初始化完成"
}

# 配置防火墙
configure_firewall() {
    log_info "配置防火墙..."

    local ports=()

    case $DEPLOY_MODE in
        portal)
            ports+=("8080/tcp" "WireGuard Portal")
            ;;
        admin)
            ports+=("8081/tcp" "WireGuard Admin")
            ;;
        agent)
            ports+=("8082/tcp" "WireGuard Agent" "51820/udp" "WireGuard VPN")
            ;;
        all)
            ports+=("8080/tcp" "WireGuard Portal" "8081/tcp" "WireGuard Admin" "8082/tcp" "WireGuard Agent" "51820/udp" "WireGuard VPN")
            ;;
    esac

    if command -v ufw &> /dev/null; then
        for ((i=0; i<${#ports[@]}; i+=2)); do
            ufw allow ${ports[i]} comment "${ports[i+1]}"
        done
        log_info "UFW 防火墙规则已添加"
    elif command -v firewall-cmd &> /dev/null; then
        for ((i=0; i<${#ports[@]}; i+=2)); do
            firewall-cmd --permanent --add-port=${ports[i]}
        done
        firewall-cmd --reload
        log_info "Firewalld 防火墙规则已添加"
    else
        log_warn "未检测到防火墙，请手动配置"
    fi
}

# 显示安装结果
show_result() {
    echo ""
    echo "=========================================="
    echo "  WireGuard 管理系统安装完成!"
    echo "=========================================="
    echo ""
    echo "部署模式: $DEPLOY_MODE"
    echo "安装目录: $INSTALL_DIR"
    echo ""

    case $DEPLOY_MODE in
        portal)
            echo "已安装服务:"
            echo "  - Portal (用户门户): http://0.0.0.0:8080"
            echo ""
            echo "启动服务:"
            echo "  systemctl start wg-portal"
            echo ""
            echo "重要提示:"
            echo "  请修改 .env 中的 ADMIN_URL 为实际的 Admin 后台地址!"
            ;;
        admin)
            echo "已安装服务:"
            echo "  - Admin (管理后台): http://127.0.0.1:8081"
            echo ""
            echo "启动服务:"
            echo "  systemctl start wg-admin"
            echo ""
            echo "默认管理员账号:"
            echo "  - 用户名: admin"
            echo "  - 密码: admin123 (请立即修改!)"
            ;;
        agent)
            echo "已安装服务:"
            echo "  - Agent (节点代理): http://127.0.0.1:8082"
            echo ""
            echo "启动服务:"
            echo "  systemctl start wg-agent"
            echo ""
            echo "提示:"
            echo "  Agent 需要在 Admin 管理后台注册后才能使用"
            ;;
        all)
            echo "已安装服务:"
            echo "  - Portal (用户门户): http://0.0.0.0:8080"
            echo "  - Admin (管理后台):  http://127.0.0.1:8081"
            echo "  - Agent (节点代理):  http://127.0.0.1:8082"
            echo ""
            echo "默认管理员账号:"
            echo "  - 用户名: admin"
            echo "  - 密码: admin123 (请立即修改!)"
            echo ""
            echo "启动服务:"
            echo "  systemctl start wg-portal wg-admin wg-agent"
            ;;
    esac

    echo ""
    echo "查看日志:"
    echo "  journalctl -u wg-$DEPLOY_MODE -f"
    echo ""
    echo "配置文件: $INSTALL_DIR/.env"
    echo ""
    echo "=========================================="
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "  WireGuard 分布式管理系统安装脚本"
    echo "=========================================="
    echo ""

    # 解析参数
    DEPLOY_MODE="all"  # portal, admin, agent, all
    SKIP_FRONTEND=0

    while [[ $# -gt 0 ]]; do
        case $1 in
            --portal)
                DEPLOY_MODE="portal"
                shift
                ;;
            --admin)
                DEPLOY_MODE="admin"
                shift
                ;;
            --agent)
                DEPLOY_MODE="agent"
                shift
                ;;
            --skip-frontend)
                SKIP_FRONTEND=1
                shift
                ;;
            --help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --portal         仅安装 Portal (用户门户)"
                echo "  --admin          仅安装 Admin (管理后台)"
                echo "  --agent          仅安装 Agent (节点代理)"
                echo "  --skip-frontend  跳过前端构建"
                echo "  --help           显示帮助信息"
                echo ""
                echo "示例:"
                echo "  $0                  # 单机模式，安装所有服务"
                echo "  $0 --portal         # 仅安装 Portal"
                echo "  $0 --admin          # 仅安装 Admin"
                echo "  $0 --agent          # 仅安装 Agent"
                exit 0
                ;;
            *)
                log_error "未知选项: $1"
                exit 1
                ;;
        esac
    done

    log_info "部署模式: $DEPLOY_MODE"

    check_root
    check_dependencies
    install_python_deps
    build_frontend
    create_directories
    generate_config
    init_database
    install_systemd_services
    configure_firewall
    show_result
}

# 执行主函数
main "$@"
