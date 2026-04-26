import sys
sys.path.insert(0, '/opt/wg-manager')

from backend.agent.utils.nftables import NftablesManager
from backend.agent.utils.tc import TcManager


class TrafficControlService:
    """流量控制服务"""

    def __init__(self, interface: str = "wg0"):
        self.interface = interface
        self.nft = NftablesManager(interface)
        self.tc = TcManager(interface)
        self._mark_counter = 100  # 标记ID计数器

    def init(self) -> bool:
        """初始化流量控制"""
        if not self.nft.init_table():
            return False
        if not self.tc.init_qdisc():
            return False
        return True

    def set_peer_limit(self, address: str, upload_mbps: int, download_mbps: int) -> bool:
        """
        设置Peer限速
        address: Peer IP地址
        upload_mbps: 上传速率(Mbps), 0表示不限速
        download_mbps: 下载速率(Mbps), 0表示不限速
        """
        if upload_mbps == 0 and download_mbps == 0:
            return self.remove_peer_limit(address)

        # 分配class ID (基于IP地址最后一段)
        try:
            class_id = int(address.split('.')[-1])
        except (ValueError, IndexError):
            class_id = self._mark_counter
            self._mark_counter += 1

        mark_id = class_id

        # 添加nftables标记
        if not self.nft.add_mark_rule(address, mark_id):
            return False

        # 添加tc类和过滤器
        rate = max(upload_mbps, download_mbps)
        if not self.tc.add_class(class_id, rate, rate):
            return False

        if not self.tc.add_filter(class_id, mark_id):
            return False

        return True

    def update_peer_limit(self, address: str, upload_mbps: int, download_mbps: int) -> bool:
        """更新Peer限速"""
        if upload_mbps == 0 and download_mbps == 0:
            return self.remove_peer_limit(address)

        try:
            class_id = int(address.split('.')[-1])
        except (ValueError, IndexError):
            class_id = self._mark_counter

        rate = max(upload_mbps, download_mbps)
        return self.tc.update_class(class_id, rate, rate)

    def remove_peer_limit(self, address: str) -> bool:
        """移除Peer限速"""
        # 移除nftables规则
        self.nft.remove_mark_rule(address)

        # 移除tc类
        try:
            class_id = int(address.split('.')[-1])
            self.tc.remove_class(class_id)
        except (ValueError, IndexError):
            pass

        return True

    def clear_all(self) -> bool:
        """清空所有限速规则"""
        self.nft.clear_table()
        self.tc.clear_all()
        return True
