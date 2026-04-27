import sys
sys.path.insert(0, '/opt/wg-manager')

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.admin.config import settings, ensure_directories
from backend.admin.database import init_db
from backend.admin.routes import auth, nodes, users, audit, admins, peers, portal

# 确保目录存在
ensure_directories()

# 初始化数据库
init_db()

app = FastAPI(
    title="WireGuard Admin",
    description="WireGuard 中央管理端",
    version="1.0.0"
)

# 注册路由
app.include_router(auth.router)
app.include_router(nodes.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(admins.router)
app.include_router(peers.router)
app.include_router(portal.router)  # Portal API 路由

# 静态文件托管
FRONTEND_DIST = Path("/opt/wg-manager/frontend/admin/dist")

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """SPA fallback - 所有未匹配的路由返回index.html"""
        file_path = FRONTEND_DIST / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")


@app.on_event("startup")
async def startup_event():
    """启动时创建默认超级管理员"""
    from backend.admin.database import SessionLocal
    from backend.admin.models import AdminUser
    from backend.shared.auth import get_password_hash
    from backend.admin.config import settings

    db = SessionLocal()
    try:
        # 检查是否存在超级管理员
        if not db.query(AdminUser).filter(AdminUser.role == "super_admin").first():
            password = settings.SUPER_ADMIN_PASSWORD[:72] if len(settings.SUPER_ADMIN_PASSWORD) > 72 else settings.SUPER_ADMIN_PASSWORD
            admin = AdminUser(
                username="admin",
                password_hash=get_password_hash(password),
                role="super_admin"
            )
            db.add(admin)
            db.commit()
            print(f"Created default super admin: admin / {password}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.ADMIN_HOST, port=settings.ADMIN_PORT)
