"""管理端接口：仪表盘、文章展示覆盖、站点设置、用户管理（踢下线/封禁）、修改密码。

全部路由经 get_admin_user 依赖保护（role=admin）。
"""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.core.redis_client import get_redis
from app.core.security import VER_KEY, hash_password, verify_password
from app.api.site import SETTINGS_CACHE_KEY, get_site_settings
from app.models.user import ArticleOverride, SiteSetting, User, ViewLog

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


# ---------------- 仪表盘 ----------------


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)) -> dict:
    total_views = await db.scalar(select(func.count(ViewLog.id))) or 0
    total_users = await db.scalar(select(func.count(User.id))) or 0
    total_articles = await db.scalar(select(func.count(func.distinct(ViewLog.slug)))) or 0
    top_result = await db.execute(
        select(ViewLog.slug, func.count(ViewLog.id).label("views"))
        .group_by(ViewLog.slug)
        .order_by(func.count(ViewLog.id).desc())
        .limit(10)
    )
    top = [{"slug": r.slug, "views": int(r.views)} for r in top_result.all()]
    return {
        "code": 0,
        "message": "ok",
        "data": {"total_views": int(total_views), "total_users": int(total_users), "articles_read": int(total_articles), "top_articles": top},
    }


# ---------------- 文章展示覆盖 ----------------


class ArticleOverrideIn(BaseModel):
    status: str = Field(pattern="^(draft|published)$")
    featured: bool = False
    pinned: bool = False
    summary: str = ""
    cover: str = ""


@router.get("/articles")
async def list_overrides(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(ArticleOverride).order_by(ArticleOverride.slug))
    rows = [
        {
            "slug": r.slug,
            "status": r.status,
            "featured": r.featured,
            "pinned": r.pinned,
            "summary": r.summary,
            "cover": r.cover,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in result.scalars()
    ]
    return {"code": 0, "message": "ok", "data": rows}


@router.put("/articles/{slug:path}")
async def upsert_override(slug: str, body: ArticleOverrideIn, db: AsyncSession = Depends(get_db)) -> dict:
    """按 slug 创建/更新展示覆盖（不改 Markdown 源文件）。"""
    result = await db.execute(select(ArticleOverride).where(ArticleOverride.slug == slug))
    row = result.scalar_one_or_none()
    if row is None:
        row = ArticleOverride(slug=slug)
        db.add(row)
    row.status = body.status
    row.featured = body.featured
    row.pinned = body.pinned
    row.summary = body.summary
    row.cover = body.cover
    await db.commit()
    return {"code": 0, "message": "ok", "data": {"slug": slug}}


@router.delete("/articles/{slug:path}")
async def delete_override(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    await db.execute(delete(ArticleOverride).where(ArticleOverride.slug == slug))
    await db.commit()
    return {"code": 0, "message": "ok", "data": None}


# ---------------- 站点设置 ----------------


class SettingsIn(BaseModel):
    """允许覆盖的站点设置键；值为 JSON 可序列化内容。"""

    values: dict[str, str]


SETTING_KEYS = {"site_name", "seo_description", "hero_intro", "announcement", "icp", "github_url", "gitee_url"}


@router.get("/settings")
async def get_settings_all(db: AsyncSession = Depends(get_db)) -> dict:
    data = await get_site_settings(db)
    return {"code": 0, "message": "ok", "data": data}


@router.put("/settings")
async def update_settings(body: SettingsIn, db: AsyncSession = Depends(get_db)) -> dict:
    unknown = set(body.values.keys()) - SETTING_KEYS
    if unknown:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持的设置项: {', '.join(unknown)}")
    for key, value in body.values.items():
        result = await db.execute(select(SiteSetting).where(SiteSetting.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            db.add(SiteSetting(key=key, value=json.dumps(value, ensure_ascii=False)))
        else:
            row.value = json.dumps(value, ensure_ascii=False)
    await db.commit()
    # 刷新 Redis 缓存，前台立即生效
    await get_redis().delete(SETTINGS_CACHE_KEY)
    return {"code": 0, "message": "ok", "data": None}


# ---------------- 用户管理 ----------------


@router.get("/users")
async def list_users(
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict:
    page = max(page, 1)
    size = min(max(size, 1), 100)
    total = await db.scalar(select(func.count(User.id))) or 0
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = [
        {
            "id": u.id,
            "username": u.username,
            "phone": u.phone,
            "nickname": u.nickname,
            "role": u.role,
            "is_banned": u.is_banned,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in result.scalars()
    ]
    return {"code": 0, "message": "ok", "data": {"total": int(total), "items": rows, "page": page, "size": size}}


@router.post("/users/{user_id}/kick")
async def kick_user(user_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """实时踢下线：INCR token_version，该用户所有旧 token 瞬时失效。"""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    user.token_version += 1
    await db.commit()
    await get_redis().set(VER_KEY.format(user_id=user.id), user.token_version)
    return {"code": 0, "message": "已踢下线", "data": None}


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: int,
    banned: bool = True,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> dict:
    """封禁/解封：封禁同时踢下线。"""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "不能封禁自己")
    user.is_banned = banned
    if banned:
        user.token_version += 1
        await get_redis().set(VER_KEY.format(user_id=user.id), user.token_version)
    await db.commit()
    return {"code": 0, "message": "已解封" if not banned else "已封禁并踢下线", "data": None}


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)


@router.post("/change-password")
async def change_password(
    body: ChangePasswordIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> dict:
    """管理员修改自己的密码（上线后首次登录必须执行）。"""
    if not admin.password_hash or not verify_password(body.old_password, admin.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "原密码错误")
    admin.password_hash = hash_password(body.new_password)
    # 改密后全端下线，要求重新登录
    admin.token_version += 1
    await db.commit()
    await get_redis().set(VER_KEY.format(user_id=admin.id), admin.token_version)
    return {"code": 0, "message": "密码已修改，请重新登录", "data": None}
