import sys
sys.path.insert(0, '/opt/wg-manager')

from fastapi import FastAPI, Depends, HTTPException, Header

from backend.shared.config import settings, ensure_directories
from backend.agent.routes.peers import router as peer_router, wg_service, traffic_service

# 确保目录存在
ensure_directories()

app = FastAPI(
    title="WireGuard Agent",
    description="WireGuard 被控客户端",
    version="1.0.0"
)

# 注册路由
app.include_router(peer_router)


def verify_api_key(x_api_key: str = Header(None)):
    """验证API密钥"""
    valid_key = settings.ENCRYPTION_KEY
    if not x_api_key or x_api_key != valid_key:
        raise HTTPException(status_code=401, detail="无效的API密钥")
    return True


@app.get("/api/status")
def get_status(authorized: bool = Depends(verify_api_key)):
    """获取WireGuard状态"""
    return wg_service.get_status()


@app.get("/api/config")
def get_config(authorized: bool = Depends(verify_api_key)):
    """获取WireGuard配置信息"""
    import subprocess
    try:
        result = subprocess.run(
            ["wg", "show", wg_service.interface],
            capture_output=True,
            text=True
        )
        return {"config": result.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """启动时初始化流量控制"""
    try:
        traffic_service.init()
        print("Traffic control initialized successfully")
    except Exception as e:
        print(f"Warning: Failed to initialize traffic control: {e}")


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "wg-agent"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.AGENT_HOST, port=settings.AGENT_PORT)
