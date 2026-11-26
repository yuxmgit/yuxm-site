"""文章接口：公开读取（前台渲染）+ 管理端增删改查（后台文章管理）。

数据源：articles 表（后台在线文章）。content/ 目录的静态文章仍由 Nuxt Content 提供。
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.models.article import Article

VALID_CATEGORIES = {"redis-cluster", "mysql", "jenkins", "docker", "jwt", "oauth2", "python-frameworks", "site"}


def serialize_article(row: Article, include_content: bool = False) -> dict:
    data = {
        "id": row.id,
        "slug": row.slug,
        "title": row.title,
        "description": row.description,
        "category": row.category,
        "tags": [t for t in row.tags.split(",") if t] if row.tags else [],
        "date": row.date.isoformat() if row.date else None,
        "series": row.series,
        "seriesOrder": row.series_order,
        "sourceRepo": row.source_repo,
        "status": row.status,
        "featured": row.featured,
        "pinned": row.pinned,
        "viewCount": row.view_count,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
    if include_content:
        data["contentMd"] = row.content_md
    return data


def slugify(title: str) -> str:
    """标题转 slug：保留字母数字连字符，中文标题回退为日期路径。"""
    import re

    s = re.sub(r"[^A-Za-z0-9]+", "-", title.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s or f"post-{date.today().isoformat()}"


# ---------------- 公开接口（前台渲染用） ----------------

public_router = APIRouter(prefix="/posts", tags=["posts"])


@public_router.get("")
async def public_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: str = Query("", description="按分类过滤，空为全部"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """已发布文章列表（置顶优先，其次日期倒序）。"""
    conds = [Article.status == "published"]
    if category:
        conds.append(Article.category == category)
    where = or_(*conds)
    total = await db.scalar(select(func.count(Article.id)).where(where)) or 0
    result = await db.execute(
        select(Article)
        .where(where)
        .order_by(Article.pinned.desc(), Article.date.desc(), Article.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {
        "code": 0,
        "message": "ok",
        "data": {"total": int(total), "page": page, "size": size, "items": [serialize_article(r) for r in result.scalars()]},
    }


@public_router.get("/{slug:path}")
async def public_detail(slug: str, db: AsyncSession = Depends(get_db)) -> dict:
    """按 slug 取已发布文章全文；404 表示无此在线文章（前端回退查静态内容）。"""
    result = await db.execute(select(Article).where(Article.slug == slug, Article.status == "published"))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文章不存在")
    return {"code": 0, "message": "ok", "data": serialize_article(row, include_content=True)}


# ---------------- 管理端 CRUD ----------------

admin_router = APIRouter(prefix="/admin/posts", tags=["admin-posts"], dependencies=[Depends(get_admin_user)])


class ArticleIn(BaseModel):
    slug: str = Field(min_length=1, max_length=256, pattern=r"^[A-Za-z0-9/._-]+$")
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=512)
    category: str = Field(default="docker")
    tags: list[str] = Field(default_factory=list)
    date: str | None = None  # YYYY-MM-DD
    series: str = ""
    seriesOrder: int | None = None
    sourceRepo: str = ""
    contentMd: str = Field(min_length=1)
    status: str = Field(default="draft", pattern="^(draft|published)$")
    featured: bool = False
    pinned: bool = False


def _parse_date(raw: str | None) -> date:
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"日期格式应为 YYYY-MM-DD: {raw}") from e


async def _check_slug_free(db: AsyncSession, slug: str, exclude_id: int | None = None) -> None:
    """slug 唯一性校验（排除自身 id）。"""
    q = select(Article).where(Article.slug == slug)
    if exclude_id is not None:
        q = q.where(Article.id != exclude_id)
    existing = (await db.execute(q)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"slug 已被在线文章占用: {slug}")


@admin_router.get("")
async def admin_list(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str = Query("", description="搜索标题/slug"),
    category: str = Query(""),
    post_status: str = Query("", alias="status", description="draft/published"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """文章列表：分页 + 关键词搜索 + 分类/状态筛选。"""
    conds = []
    if q:
        like = f"%{q}%"
        conds.append(or_(Article.title.like(like), Article.slug.like(like)))
    if category:
        conds.append(Article.category == category)
    if post_status:
        conds.append(Article.status == post_status)
    where = or_(*conds) if conds else True
    total = await db.scalar(select(func.count(Article.id)).where(where)) or 0
    result = await db.execute(
        select(Article)
        .where(where)
        .order_by(Article.updated_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {
        "code": 0,
        "message": "ok",
        "data": {"total": int(total), "page": page, "size": size, "items": [serialize_article(r) for r in result.scalars()]},
    }


@admin_router.post("")
async def admin_create(body: ArticleIn, db: AsyncSession = Depends(get_db)) -> dict:
    """新建文章：slug 冲突返回 409；status=published 时立即对前台可见。"""
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持分类: {body.category}")
    await _check_slug_free(db, body.slug)
    row = Article(
        slug=body.slug,
        title=body.title,
        description=body.description,
        category=body.category,
        tags=",".join(t.strip() for t in body.tags if t.strip())[:512],
        date=_parse_date(body.date),
        series=body.series,
        series_order=body.seriesOrder,
        source_repo=body.sourceRepo,
        content_md=body.contentMd,
        status=body.status,
        featured=body.featured,
        pinned=body.pinned,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"code": 0, "message": "创建成功", "data": {"id": row.id, "slug": row.slug}}


@admin_router.get("/{article_id}")
async def admin_detail(article_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """取单篇全文（编辑器回填）。"""
    row = await db.get(Article, article_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文章不存在")
    return {"code": 0, "message": "ok", "data": serialize_article(row, include_content=True)}


@admin_router.put("/{article_id}")
async def admin_update(article_id: int, body: ArticleIn, db: AsyncSession = Depends(get_db)) -> dict:
    """更新文章（全字段覆盖提交）。"""
    row = await db.get(Article, article_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文章不存在")
    if body.category not in VALID_CATEGORIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"不支持分类: {body.category}")
    await _check_slug_free(db, body.slug, exclude_id=article_id)
    row.slug = body.slug
    row.title = body.title
    row.description = body.description
    row.category = body.category
    row.tags = ",".join(t.strip() for t in body.tags if t.strip())[:512]
    row.date = _parse_date(body.date)
    row.series = body.series
    row.series_order = body.seriesOrder
    row.source_repo = body.sourceRepo
    row.content_md = body.contentMd
    row.status = body.status
    row.featured = body.featured
    row.pinned = body.pinned
    await db.commit()
    return {"code": 0, "message": "已保存", "data": {"id": row.id, "slug": row.slug}}


@admin_router.delete("/{article_id}")
async def admin_delete(article_id: int, db: AsyncSession = Depends(get_db)) -> dict:
    """删除文章（物理删除，前台立即不可见）。"""
    row = await db.get(Article, article_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文章不存在")
    await db.delete(row)
    await db.commit()
    return {"code": 0, "message": "已删除", "data": None}


class BatchIn(BaseModel):
    action: str = Field(pattern="^(publish|draft|feature|unfeature|delete)$")
    ids: list[int]


@admin_router.post("/batch")
async def admin_batch(body: BatchIn, db: AsyncSession = Depends(get_db)) -> dict:
    """批量操作：发布/转草稿/精选/取消精选/删除。"""
    if not body.ids:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "未选择文章")
    if body.action == "delete":
        await db.execute(delete(Article).where(Article.id.in_(body.ids)))
        await db.commit()
        return {"code": 0, "message": f"已删除 {len(body.ids)} 篇", "data": None}
    result = await db.execute(select(Article).where(Article.id.in_(body.ids)))
    rows = result.scalars().all()
    for r in rows:
        if body.action == "publish":
            r.status = "published"
        elif body.action == "draft":
            r.status = "draft"
        elif body.action == "feature":
            r.featured = True
        elif body.action == "unfeature":
            r.featured = False
    await db.commit()
    return {"code": 0, "message": f"已更新 {len(rows)} 篇", "data": None}


class FlagsIn(BaseModel):
    """快捷更新：仅状态/精选/置顶，不动正文。"""

    status: str | None = Field(default=None, pattern="^(draft|published)$")
    featured: bool | None = None
    pinned: bool | None = None


@admin_router.patch("/{article_id}/flags")
async def admin_patch_flags(article_id: int, body: FlagsIn, db: AsyncSession = Depends(get_db)) -> dict:
    """列表页快捷开关：状态/精选/置顶，正文与 slug 保持不变。"""
    row = await db.get(Article, article_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "文章不存在")
    if body.status is not None:
        row.status = body.status
    if body.featured is not None:
        row.featured = body.featured
    if body.pinned is not None:
        row.pinned = body.pinned
    await db.commit()
    return {"code": 0, "message": "已更新", "data": {"id": row.id}}
