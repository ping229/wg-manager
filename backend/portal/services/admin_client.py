import httpx
from typing import Optional, List, Dict, Any
from backend.portal.config import settings


class AdminClient:
    """Admin API 客户端 - Portal 用于调用 Admin 服务"""

    def __init__(self):
        self.base_url = settings.ADMIN_URL.rstrip('/')
        self.api_key = settings.ADMIN_API_KEY
        self.timeout = 10.0

    def _get_headers(self) -> dict:
        return {"X-Admin-API-Key": self.api_key} if self.api_key else {}

    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送请求到 Admin API"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(url, headers=headers, timeout=self.timeout)
                elif method == "POST":
                    response = await client.post(url, json=data, headers=headers, timeout=self.timeout)
                elif method == "PUT":
                    response = await client.put(url, json=data, headers=headers, timeout=self.timeout)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if response.status_code == 401:
                    raise Exception("Admin API 认证失败，请检查 ADMIN_API_KEY 配置")
                if response.status_code == 403:
                    raise Exception("Admin API 权限不足")
                if response.status_code != 200:
                    error_detail = response.json().get("detail", response.text)
                    raise Exception(f"Admin API 错误: {error_detail}")

                return response.json()
            except httpx.RequestError as e:
                raise Exception(f"Admin 服务连接失败: {str(e)}")

    # 节点相关
    async def get_nodes(self) -> List[Dict]:
        """获取节点列表"""
        return await self._request("GET", "/api/portal/nodes")

    async def get_node(self, node_id: int) -> Dict:
        """获取节点详情"""
        return await self._request("GET", f"/api/portal/nodes/{node_id}")

    # Peer 相关
    async def get_peer(self, user_id: int) -> Optional[Dict]:
        """获取用户的 Peer 配置"""
        try:
            return await self._request("GET", f"/api/portal/peer/{user_id}")
        except Exception as e:
            if "不存在" in str(e):
                return None
            raise e

    async def create_peer(self, user_id: int, username: str, node_id: int,
                          mtu: int = None, dns: str = None, keepalive: int = None) -> Dict:
        """创建 Peer 配置"""
        data = {
            "user_id": user_id,
            "username": username,
            "node_id": node_id,
            "mtu": mtu,
            "dns": dns,
            "keepalive": keepalive
        }
        return await self._request("POST", "/api/portal/peer", data)

    async def update_peer_settings(self, user_id: int, mtu: int = None,
                                   dns: str = None, keepalive: int = None) -> Dict:
        """更新 Peer 设置"""
        data = {"mtu": mtu, "dns": dns, "keepalive": keepalive}
        return await self._request("PUT", f"/api/portal/peer/{user_id}/settings", data)

    async def delete_peer(self, user_id: int) -> Dict:
        """删除 Peer 配置"""
        return await self._request("DELETE", f"/api/portal/peer/{user_id}")

    async def get_peer_config(self, user_id: int) -> str:
        """获取 Peer 配置文件内容"""
        url = f"{self.base_url}/api/portal/peer/{user_id}/config"
        headers = self._get_headers()

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=self.timeout)
            if response.status_code != 200:
                raise Exception(f"获取配置失败: {response.text}")
            return response.text


# 全局客户端实例
admin_client = AdminClient()
