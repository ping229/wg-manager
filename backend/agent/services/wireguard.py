import subprocess
import os
from pathlib import Path
from typing import Optional

import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.shared.config import settings


class WireGuardService:
    """WireGuard服务操作类"""

    def __init__(self, interface: str = "wg0"):
        self.interface = interface
        self.config_path = Path(f"/etc/wireguard/{interface}.conf")

    def get_public_key(self) -> Optional[str]:
        """获取接口公钥"""
        try:
            result = subprocess.run(
                ["wg", "show", self.interface, "public-key"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def get_listen_port(self) -> Optional[int]:
        """获取监听端口"""
        try:
            result = subprocess.run(
                ["wg", "show", self.interface, "listen-port"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
        except Exception:
            pass
        return None

    def get_peers(self) -> list[dict]:
        """获取所有Peer"""
        peers = []
        try:
            result = subprocess.run(
                ["wg", "show", self.interface, "peers"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        peers.append({"public_key": line.strip()})
        except Exception:
            pass
        return peers

    def add_peer(self, public_key: str, address: str) -> bool:
        """添加Peer"""
        try:
            # 使用wg命令添加peer
            subprocess.run(
                ["wg", "set", self.interface, "peer", public_key, "allowed-ips", f"{address}/32"],
                check=True
            )

            # 保存配置到文件
            self._save_peer_to_config(public_key, address)
            return True
        except subprocess.CalledProcessError as e:
            print(f"添加Peer失败: {e}")
            return False

    def remove_peer(self, public_key: str) -> bool:
        """删除Peer"""
        try:
            subprocess.run(
                ["wg", "set", self.interface, "peer", public_key, "remove"],
                check=True
            )

            # 从配置文件中删除
            self._remove_peer_from_config(public_key)
            return True
        except subprocess.CalledProcessError as e:
            print(f"删除Peer失败: {e}")
            return False

    def clear_peers(self) -> int:
        """清空所有Peer,返回删除的数量"""
        peers = self.get_peers()
        count = 0
        for peer in peers:
            if self.remove_peer(peer["public_key"]):
                count += 1
        return count

    def _save_peer_to_config(self, public_key: str, address: str):
        """保存Peer到配置文件"""
        if not self.config_path.exists():
            return

        peer_config = f"""
[Peer]
PublicKey = {public_key}
AllowedIPs = {address}/32
"""
        with open(self.config_path, 'a') as f:
            f.write(peer_config)

    def _remove_peer_from_config(self, public_key: str):
        """从配置文件中删除Peer"""
        if not self.config_path.exists():
            return

        with open(self.config_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        skip = False
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.strip() == "[Peer]":
                # 检查接下来的几行是否包含该public key
                j = i + 1
                found = False
                while j < len(lines) and not lines[j].strip().startswith("["):
                    if f"PublicKey = {public_key}" in lines[j]:
                        found = True
                        break
                    j += 1
                if found:
                    # 跳过这个Peer块
                    i = j + 1
                    while i < len(lines) and not lines[i].strip().startswith("["):
                        i += 1
                    continue
            new_lines.append(line)
            i += 1

        with open(self.config_path, 'w') as f:
            f.writelines(new_lines)

    def is_running(self) -> bool:
        """检查WireGuard是否正在运行"""
        try:
            result = subprocess.run(
                ["wg", "show", self.interface],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_status(self) -> dict:
        """获取状态信息"""
        return {
            "interface": self.interface,
            "public_key": self.get_public_key(),
            "listen_port": self.get_listen_port(),
            "peer_count": len(self.get_peers()),
            "running": self.is_running()
        }
