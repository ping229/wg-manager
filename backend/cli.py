#!/usr/bin/env python3
"""
WireGuard 管理系统命令行工具

用法:
  python -m backend.cli --regenerate-key       # 重新生成 KEY
  python -m backend.cli --show-key             # 显示当前 KEY
  python -m backend.cli --help                 # 显示帮助
"""

import sys
import os
import argparse
import secrets

# 添加项目路径
sys.path.insert(0, '/opt/wg-manager')


def get_env_file():
    """获取 .env 文件路径"""
    return '/opt/wg-manager/.env'


def read_env_file():
    """读取 .env 文件"""
    env_file = get_env_file()
    if not os.path.exists(env_file):
        return None, {}

    with open(env_file, 'r') as f:
        content = f.read()

    # 解析键值对
    env_vars = {}
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            env_vars[key.strip()] = value.strip()

    return content, env_vars


def write_env_file(env_vars, original_content):
    """写入 .env 文件，保留注释和格式"""
    env_file = get_env_file()

    lines = original_content.split('\n') if original_content else []
    new_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            if key in env_vars:
                # 保留原始缩进
                indent = len(line) - len(line.lstrip())
                new_lines.append(' ' * indent + f"{key}={env_vars[key]}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # 添加新的变量
    existing_keys = set()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            key = stripped.split('=', 1)[0].strip()
            existing_keys.add(key)

    for key, value in env_vars.items():
        if key not in existing_keys:
            new_lines.append(f"{key}={value}")

    with open(env_file, 'w') as f:
        f.write('\n'.join(new_lines))

    # 设置权限
    os.chmod(env_file, 0o600)


def regenerate_key():
    """重新生成 KEY"""
    # 生成新的 KEY (32 字节 = 64 字符 hex)
    new_key = secrets.token_hex(16)

    original_content, env_vars = read_env_file()
    if original_content is None:
        print("错误: .env 文件不存在")
        sys.exit(1)

    old_key = env_vars.get('KEY', '')

    # 更新 KEY
    env_vars['KEY'] = new_key
    write_env_file(env_vars, original_content)

    print("=" * 50)
    print("KEY 已重新生成!")
    print("=" * 50)
    if old_key:
        print(f"旧 KEY: {old_key[:8]}****{old_key[-8:] if len(old_key) > 16 else ''}")
    print(f"新 KEY: {new_key}")
    print("=" * 50)
    print("")
    print("请确保在相关服务中更新此 KEY:")
    print("  - Portal: 确保 .env 中的 KEY 与 Admin 端配置相同")
    print("  - Agent:  确保 .env 中的 KEY 与 Admin 端节点配置相同")
    print("  - Admin:  在 'Portal 站点管理' 或 '节点管理' 中更新对应的 KEY")
    print("")
    print("更新后请重启服务:")
    print("  systemctl restart wg-portal wg-admin wg-agent")


def show_key():
    """显示当前 KEY"""
    original_content, env_vars = read_env_file()
    if original_content is None:
        print("错误: .env 文件不存在")
        sys.exit(1)

    key = env_vars.get('KEY', '')

    print("=" * 50)
    print("当前配置")
    print("=" * 50)
    print(f"KEY: {key if key else '(未设置)'}")
    print(f"SECRET_KEY: {env_vars.get('SECRET_KEY', '')[:16]}****")
    print(f"ENCRYPTION_KEY: {env_vars.get('ENCRYPTION_KEY', '')}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='WireGuard 管理系统命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m backend.cli --regenerate-key    重新生成 KEY
  python -m backend.cli --show-key          显示当前 KEY
        """
    )

    parser.add_argument(
        '--regenerate-key',
        action='store_true',
        help='重新生成 KEY'
    )

    parser.add_argument(
        '--show-key',
        action='store_true',
        help='显示当前 KEY'
    )

    args = parser.parse_args()

    if args.regenerate_key:
        regenerate_key()
    elif args.show_key:
        show_key()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
