import subprocess
from typing import Optional


class TcManager:
    """tc流量控制管理类"""

    DEFAULT_HANDLE = "1:"
    ROOT_CLASS = "1:1"
    DEFAULT_RATE = "1000mbit"  # 默认根速率

    def __init__(self, interface: str = "wg0"):
        self.interface = interface

    def _run_tc(self, command: str) -> bool:
        """执行tc命令"""
        try:
            subprocess.run(
                f"tc {command}",
                shell=True,
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError as e:
            print(f"tc命令执行失败: {e.stderr.decode() if e.stderr else str(e)}")
            return False

    def init_qdisc(self) -> bool:
        """初始化qdisc"""
        # 删除旧的qdisc
        self._run_tc(f"qdisc del dev {self.interface} root 2>/dev/null")

        # 创建HTB qdisc
        if not self._run_tc(f"qdisc add dev {self.interface} root handle {self.DEFAULT_HANDLE} htb default 999"):
            return False

        # 创建根类
        return self._run_tc(
            f"class add dev {self.interface} parent {self.DEFAULT_HANDLE} classid {self.ROOT_CLASS} htb rate {self.DEFAULT_RATE}"
        )

    def add_class(self, class_id: int, rate_mbps: int, ceil_mbps: Optional[int] = None) -> bool:
        """
        添加限速类
        class_id: 类ID (1-999)
        rate_mbps: 保证速率(Mbps)
        ceil_mbps: 最大速率(Mbps),默认等于保证速率
        """
        if ceil_mbps is None:
            ceil_mbps = rate_mbps

        classid = f"1:{class_id}"
        rate = f"{rate_mbps}mbit"
        ceil = f"{ceil_mbps}mbit"

        return self._run_tc(
            f"class add dev {self.interface} parent {self.ROOT_CLASS} classid {classid} htb rate {rate} ceil {ceil}"
        )

    def update_class(self, class_id: int, rate_mbps: int, ceil_mbps: Optional[int] = None) -> bool:
        """更新限速类"""
        if ceil_mbps is None:
            ceil_mbps = rate_mbps

        classid = f"1:{class_id}"
        rate = f"{rate_mbps}mbit"
        ceil = f"{ceil_mbps}mbit"

        return self._run_tc(
            f"class change dev {self.interface} parent {self.ROOT_CLASS} classid {classid} htb rate {rate} ceil {ceil}"
        )

    def remove_class(self, class_id: int) -> bool:
        """删除限速类"""
        classid = f"1:{class_id}"
        return self._run_tc(f"class del dev {self.interface} classid {classid}")

    def add_filter(self, class_id: int, mark: int) -> bool:
        """添加过滤器,将标记的流量路由到指定类"""
        return self._run_tc(
            f"filter add dev {self.interface} parent {self.DEFAULT_HANDLE} protocol ip handle {mark} fw classid 1:{class_id}"
        )

    def remove_filter(self, mark: int) -> bool:
        """删除过滤器"""
        return self._run_tc(
            f"filter del dev {self.interface} parent {self.DEFAULT_HANDLE} protocol ip handle {mark} fw"
        )

    def set_rate_limit(self, class_id: int, upload_mbps: int, download_mbps: int) -> bool:
        """
        设置上传和下载限速
        upload_mbps: 上传速率(Mbps), 0表示不限速
        download_mbps: 下载速率(Mbps), 0表示不限速
        """
        # 简化实现: 取两个值的较大者作为总速率
        if upload_mbps == 0 and download_mbps == 0:
            return self.remove_class(class_id)

        rate = max(upload_mbps, download_mbps)
        return self.add_class(class_id, rate, rate)

    def clear_all(self) -> bool:
        """清空所有tc规则"""
        return self._run_tc(f"qdisc del dev {self.interface} root")

    def show_classes(self) -> list[str]:
        """显示所有类"""
        try:
            result = subprocess.run(
                f"tc class show dev {self.interface}",
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except Exception:
            pass
        return []
