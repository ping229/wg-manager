import subprocess
from typing import Optional


class NftablesManager:
    """nftables管理类"""

    TABLE_NAME = "wg_traffic"
    CHAIN_NAME = "wg_mark"

    def __init__(self, interface: str = "wg0"):
        self.interface = interface

    def _run_nft(self, command: str) -> bool:
        """执行nft命令"""
        try:
            subprocess.run(
                f"nft {command}",
                shell=True,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"nft命令执行失败: {e}")
            return False

    def init_table(self) -> bool:
        """初始化nftables表"""
        commands = [
            f"add table inet {self.TABLE_NAME}",
            f"add chain inet {self.TABLE_NAME} {self.CHAIN_NAME} {{ type filter hook forward priority 0 ; }}",
        ]
        for cmd in commands:
            if not self._run_nft(cmd):
                return False
        return True

    def add_mark_rule(self, address: str, mark_id: int) -> bool:
        """添加流量标记规则"""
        # 入站流量标记
        cmd = f'add rule inet {self.TABLE_NAME} {self.CHAIN_NAME} ip daddr {address} meta mark set {mark_id}'
        if not self._run_nft(cmd):
            return False

        # 出站流量标记
        cmd = f'add rule inet {self.TABLE_NAME} {self.CHAIN_NAME} ip saddr {address} meta mark set {mark_id}'
        return self._run_nft(cmd)

    def remove_mark_rule(self, address: str) -> bool:
        """删除流量标记规则"""
        # 获取规则句柄
        try:
            result = subprocess.run(
                f"nft -a list table inet {self.TABLE_NAME}",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return False

            handles = []
            for line in result.stdout.split('\n'):
                if address in line and 'handle' in line:
                    parts = line.split('handle')
                    if len(parts) > 1:
                        handles.append(parts[1].strip())

            # 删除规则
            for handle in handles:
                self._run_nft(f'delete rule inet {self.TABLE_NAME} {self.CHAIN_NAME} handle {handle}')

            return True
        except Exception as e:
            print(f"删除标记规则失败: {e}")
            return False

    def clear_table(self) -> bool:
        """清空表"""
        return self._run_nft(f"delete table inet {self.TABLE_NAME}")
