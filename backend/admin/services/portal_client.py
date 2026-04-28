import httpx
from typing import Optional, List, Dict
from backend.admin.config import settings


class PortalClient:
    """Portal API 客户端 - Admin 用于调用指定 Portal 服务"""

    def __init__(self, url: str = None, key: str = None):
        self.base_url = (url or settings.PORTAL_URL).rstrip('/')
        self.key = key
        self.timeout = 10.0

    def _get_headers(self) -> dict:
        return {"X-Key": self.key} if self.key else {}

    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送请求到 Portal API"""
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
                    raise Exception("Portal API 认证失败")
                if response.status_code == 403:
                    raise Exception("Portal API 权限不足")
                if response.status_code != 200:
                    error_detail = response.json().get("detail", response.text)
                    raise Exception(f"Portal API 错误: {error_detail}")

                return response.json()
            except httpx.RequestError as e:
                raise Exception(f"Portal 服务连接失败: {str(e)}")

    # 用户相关
    async def get_users(self) -> List[Dict]:
        """获取用户列表"""
        return await self._request("GET", "/api/auth/admin/users")

    async def get_user(self, user_id: int) -> Dict:
        """获取用户详情"""
        return await self._request("GET", f"/api/auth/admin/user/{user_id}")

    async def update_user_status(self, user_id: int, status: str) -> Dict:
        """更新用户状态"""
        return await self._request("PUT", f"/api/auth/admin/user/{user_id}/status?status={status}")

    # 注册申请相关
    async def get_registrations(self, status: str = None) -> List[Dict]:
        """获取注册申请列表"""
        endpoint = "/api/auth/admin/registrations"
        if status:
            endpoint += f"?status_filter={status}"
        return await self._request("GET", endpoint)

    async def approve_registration(self, reg_id: int) -> Dict:
        """批准注册申请"""
        return await self._request("POST", f"/api/auth/admin/approve/{reg_id}")

    async def reject_registration(self, reg_id: int, reason: str = "") -> Dict:
        """拒绝注册申请"""
        return await self._request("POST", f"/api/auth/admin/reject/{reg_id}?reason={reason}")

    # 用户创建/删除
    async def create_user(self, username: str, password: str, email: str) -> Dict:
        """创建用户"""
        return await self._request("POST", "/api/auth/admin/users/create", {
            "username": username,
            "password": password,
            "email": email
        })

    async def batch_create_users(self, users: List[Dict]) -> Dict:
        """批量创建用户"""
        return await self._request("POST", "/api/auth/admin/users/batch-create", {"users": users})

    async def delete_user(self, user_id: int) -> Dict:
        """删除用户"""
        return await self._request("DELETE", f"/api/auth/admin/user/{user_id}")

    async def batch_delete_users(self, user_ids: List[int]) -> Dict:
        """批量删除用户"""
        return await self._request("POST", "/api/auth/admin/users/batch-delete", {"user_ids": user_ids})

    async def update_user_password(self, user_id: int, password: str) -> Dict:
        """修改用户密码"""
        return await self._request("PUT", f"/api/auth/admin/user/{user_id}/password", {"password": password})

    # 健康检查
    async def health_check(self) -> bool:
        """检查 Portal 是否在线"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health", timeout=3.0)
                return response.status_code == 200
        except:
            return False


def get_portal_client(portal_site) -> PortalClient:
    """根据 Portal 站点配置创建客户端"""
    key = portal_site.key or ""
    return PortalClient(url=portal_site.url, key=key)
