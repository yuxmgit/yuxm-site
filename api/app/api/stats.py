"""阅读数统计：POST 上报 + GET 查询（Redis 缓存 + MySQL 落库）。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.user import ViewLog

router = APIRouter(prefix="/stats", tags=["stats"])

VIEWS_KEY = "stats:views:{slug}"
CACHE_TTL = 60


async def _get_views(db: AsyncSession, slug: str) -> int:
    redis = get_redis()
    key = VIEWS_KEY.format(slug=slug)
    cached = await redis.get(key)
    if cached is not None:
        return int(cached)
    result = await db.execute(select(func.count(ViewLog.id)).where(ViewLog.slug == slug))
    total = int(result.scalar() or 0)
    await redis.set(key, total, ex=CACHE_TTL)
    return total


@router.get("/views/{slug:path}")
async def get_views(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    return {"code": 0, "message": "ok", "data": {"slug": slug, "views": await _get_views(db, slug)}}


@router.post("/views/{slug:path}")
async def add_view(slug: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """阅读数上报：同一 IP 对同一文章 60 秒内只计一次（防刷新刷量）。"""
    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    dedup_key = f"ratelimit:views:{ip}:{slug}"
    if not await redis.exists(dedup_key):
        db.add(ViewLog(slug=slug, ip=ip))
        await db.commit()
        await redis.set(dedup_key, 1, ex=60)
        await redis.delete(VIEWS_KEY.format(slug=slug))
    return {"code": 0, "message": "ok", "data": {"views": await _get_views(db, slug)}}


@router.get("/top")
async def top_articles(limit: int = 10, db: AsyncSession = Depends(get_db)) -> dict:
    """阅读数 Top 文章（后台看板用）。"""
    result = await db.execute(
        select(ViewLog.slug, func.count(ViewLog.id).label("views"))
        .group_by(ViewLog.slug)
        .order_by(func.count(ViewLog.id).desc())
        .limit(limit)
    )
    rows = [{"slug": r.slug, "views": int(r.views)} for r in result.all()]
    return {"code": 0, "message": "ok", "data": rows}
