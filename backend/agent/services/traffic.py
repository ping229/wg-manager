import sys
import subprocess
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
        self._initialized = False
        self._init_error = None

    def _check_interface_exists(self) -> bool:
        """检查WireGuard接口是否存在"""
        try:
            result = subprocess.run(
                ["ip", "link", "show", self.interface],
                capture_output=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def init(self) -> bool:
        """初始化流量控制"""
        # 检查接口是否存在
        if not self._check_interface_exists():
            self._init_error = f"接口 {self.interface} 不存在"
            print(f"Warning: {self._init_error}")
            return False

        if not self.nft.init_table():
            self._init_error = "nftables初始化失败"
            return False
        if not self.tc.init_qdisc():
            self._init_error = "tc qdisc初始化失败"
            return False

        self._initialized = True
        self._init_error = None
        return True

    def ensure_initialized(self) -> tuple[bool, str]:
        """确保流量控制已初始化"""
        if self._initialized:
            return True, None

        # 尝试重新初始化
        if self.init():
            return True, None

        return False, self._init_error or "流量控制未初始化"

    def _get_class_id(self, address: str) -> int:
        """根据IP地址生成唯一的class_id (10-999)"""
        try:
            # 将IP地址转换为唯一整数
            parts = address.split('.')
            class_id = (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
            # 映射到 10-999 范围
            return 10 + (class_id % 990)
        except (ValueError, IndexError):
            # 解析失败时使用计数器
            self._mark_counter += 1
            return self._mark_counter

    def set_peer_limit(self, address: str, upload_mbps: int, download_mbps: int) -> tuple[bool, str]:
        """
        设置Peer限速
        address: Peer IP地址
        upload_mbps: 上传速率(Mbps), 0表示不限速
        download_mbps: 下载速率(Mbps), 0表示不限速
        返回: (成功与否, 错误信息)
        """
        if upload_mbps == 0 and download_mbps == 0:
            success = self.remove_peer_limit(address)
            return success, None if success else "移除限速失败"

        # 确保已初始化
        ok, err = self.ensure_initialized()
        if not ok:
            return False, err

        # 分配class ID (基于完整IP地址生成)
        class_id = self._get_class_id(address)
        mark_id = class_id

        # 添加nftables标记
        if not self.nft.add_mark_rule(address, mark_id):
            return False, "添加nftables标记规则失败"

        # 添加tc类和过滤器
        rate = max(upload_mbps, download_mbps)
        if not self.tc.add_class(class_id, rate, rate):
            return False, "添加tc限速类失败"

        if not self.tc.add_filter(class_id, mark_id):
            return False, "添加tc过滤器失败"

        return True, None

    def update_peer_limit(self, address: str, upload_mbps: int, download_mbps: int) -> bool:
        """更新Peer限速"""
        if upload_mbps == 0 and download_mbps == 0:
            return self.remove_peer_limit(address)

        class_id = self._get_class_id(address)
        rate = max(upload_mbps, download_mbps)
        return self.tc.update_class(class_id, rate, rate)

    def remove_peer_limit(self, address: str) -> bool:
        """移除Peer限速"""
        # 移除nftables规则
        self.nft.remove_mark_rule(address)

        # 移除tc类
        class_id = self._get_class_id(address)
        self.tc.remove_class(class_id)

        return True

    def clear_all(self) -> bool:
        """清空所有限速规则"""
        self.nft.clear_table()
        self.tc.clear_all()
        return True
