"""公开的站点设置接口：前台 SSR 读取（Redis 缓存，后台修改时刷新缓存）。"""
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.user import SiteSetting

router = APIRouter(prefix="/site", tags=["site"])

SETTINGS_CACHE_KEY = "settings:site"


async def get_site_settings(db: AsyncSession) -> dict:
    """读取站点设置（JSON 键值），优先 Redis 缓存。"""
    redis = get_redis()
    cached = await redis.get(SETTINGS_CACHE_KEY)
    if cached:
        return json.loads(cached)

    result = await db.execute(select(SiteSetting))
    settings_map = {}
    for row in result.scalars():
        try:
            settings_map[row.key] = json.loads(row.value)
        except (ValueError, TypeError):
            settings_map[row.key] = row.value
    await redis.set(SETTINGS_CACHE_KEY, json.dumps(settings_map, ensure_ascii=False), ex=300)
    return settings_map


@router.get("/settings")
async def site_settings(db: AsyncSession = Depends(get_db)) -> dict:
    data = await get_site_settings(db)
    return {"code": 0, "message": "ok", "data": data}
