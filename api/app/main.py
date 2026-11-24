"""FastAPI 应用入口。

职责：装配路由、CORS、统一响应格式、异常处理、生命周期（Redis 连接）。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import Base, engine
from app.core.redis_client import close_redis, get_redis

API_PREFIX = "/api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时预热 Redis 连接，失败立即暴露配置问题
    await get_redis().ping()
    # 开发环境自动建表；生产使用 alembic 迁移
    if settings.app_env == "dev":
        from app import models  # noqa: F401  确保模型已注册

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title="yuxm-site API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if settings.app_env == "prod" else "/api/docs",
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):  # noqa: ANN001
        # 统一 HTTPException 响应格式为 {code, message}，前端直接读 message 展示
        # （含登录锁定的"请 X 分钟后再试"等业务提示）
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": str(exc.detail)},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc):  # noqa: ANN001
        # 统一兜底：任何未处理异常返回 500，不向客户端泄漏堆栈
        return JSONResponse(status_code=500, content={"code": 500, "message": "服务器内部错误"})

    @app.get("/api/health")
    async def health() -> dict:
        return {"code": 0, "message": "ok", "data": {"env": settings.app_env}}

    from app.api.admin import router as admin_router
    from app.api.auth import router as auth_router
    from app.api.interactive import router as interactive_router
    from app.api.site import router as site_router
    from app.api.stats import router as stats_router

    app.include_router(auth_router, prefix=API_PREFIX)
    app.include_router(stats_router, prefix=API_PREFIX)
    app.include_router(site_router, prefix=API_PREFIX)
    app.include_router(interactive_router, prefix=API_PREFIX)
    app.include_router(admin_router, prefix=API_PREFIX)

    return app


app = create_app()
