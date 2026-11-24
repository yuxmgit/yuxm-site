"""社区互动路由：文章点赞/收藏状态、评论（一层回复）、个人笔记、个人中心数据。

权限模型：
- 点赞/收藏/评论发表/笔记读写：需登录（get_current_user）
- 点赞数/收藏数/评论列表：公开（get_optional_user，登录则附带本人状态）
- 评论删除：作者本人或管理员
- 笔记为用户私有数据，任何人（含管理员）只能读写自己的
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.community import Comment, Favorite, Like, Note
from app.models.user import User

router = APIRouter(prefix="/interactive", tags=["interactive"])

SLUG_MAX = 256
COMMENT_MAX = 500
NOTE_MAX = 20000


def _check_slug(slug: str) -> None:
    if not slug or len(slug) > SLUG_MAX:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "无效的文章路径")


def _user_brief(user: User) -> dict:
    return {"id": user.id, "nickname": user.nickname or f"用户{user.id}", "avatar": user.avatar}


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=COMMENT_MAX)
    parent_id: int | None = None


class NoteSaveRequest(BaseModel):
    content: str = Field(max_length=NOTE_MAX)


# ---------------- 点赞 / 收藏 ----------------


@router.get("/{slug:path}/status")
async def interactive_status(
    slug: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """文章互动状态总览：公开计数 + （登录时）本人是否点过赞/收藏过。"""
    _check_slug(slug)
    likes = await db.scalar(select(func.count()).select_from(Like).where(Like.slug == slug)) or 0
    favorites = await db.scalar(select(func.count()).select_from(Favorite).where(Favorite.slug == slug)) or 0
    comments = await db.scalar(
        select(func.count()).select_from(Comment).where(Comment.slug == slug, Comment.is_deleted.is_(False))
    ) or 0
    liked = favorited = False
    if user is not None:
        liked = await db.scalar(
            select(func.count()).select_from(Like).where(Like.user_id == user.id, Like.slug == slug)
        ) > 0
        favorited = await db.scalar(
            select(func.count()).select_from(Favorite).where(Favorite.user_id == user.id, Favorite.slug == slug)
        ) > 0
    return {
        "code": 0,
        "message": "ok",
        "data": {"likes": likes, "favorites": favorites, "comments": comments, "liked": liked, "favorited": favorited},
    }


@router.post("/{slug:path}/like")
async def toggle_like(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """点赞/取消点赞（幂等切换）。"""
    _check_slug(slug)
    existing = await db.scalar(select(Like).where(Like.user_id == user.id, Like.slug == slug))
    if existing:
        await db.delete(existing)
        liked = False
    else:
        db.add(Like(user_id=user.id, slug=slug))
        liked = True
    await db.commit()
    likes = await db.scalar(select(func.count()).select_from(Like).where(Like.slug == slug)) or 0
    return {"code": 0, "message": "ok", "data": {"liked": liked, "likes": likes}}


@router.post("/{slug:path}/favorite")
async def toggle_favorite(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """收藏/取消收藏（幂等切换）。"""
    _check_slug(slug)
    existing = await db.scalar(select(Favorite).where(Favorite.user_id == user.id, Favorite.slug == slug))
    if existing:
        await db.delete(existing)
        favorited = False
    else:
        db.add(Favorite(user_id=user.id, slug=slug))
        favorited = True
    await db.commit()
    favorites = await db.scalar(select(func.count()).select_from(Favorite).where(Favorite.slug == slug)) or 0
    return {"code": 0, "message": "ok", "data": {"favorited": favorited, "favorites": favorites}}


# ---------------- 评论 ----------------


@router.get("/{slug:path}/comments")
async def comment_list(
    slug: str,
    user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """评论列表（根评论 + 一层回复），公开可读；登录用户额外拿到可删除标记。"""
    _check_slug(slug)
    result = await db.execute(
        select(Comment, User.nickname, User.avatar)
        .join(User, User.id == Comment.user_id)
        .where(Comment.slug == slug)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    rows = result.all()
    items: dict[int, dict] = {}
    roots: list[dict] = []
    total = 0
    for comment, nickname, avatar in rows:
        if not comment.is_deleted:
            total += 1
        item = {
            "id": comment.id,
            "parent_id": comment.parent_id,
            "content": "" if comment.is_deleted else comment.content,
            "is_deleted": comment.is_deleted,
            "created_at": comment.created_at.isoformat(),
            "user": {"id": comment.user_id, "nickname": nickname or f"用户{comment.user_id}", "avatar": avatar},
            "can_delete": bool(user and (user.id == comment.user_id or user.role == "admin")) and not comment.is_deleted,
            "replies": [],
        }
        items[comment.id] = item
        if comment.parent_id is None:
            roots.append(item)
        else:
            parent = items.get(comment.parent_id)
            if parent is not None:
                parent["replies"].append(item)
            else:
                roots.append(item)  # 父评论异常缺失时降级为根评论展示
    return {"code": 0, "message": "ok", "data": {"total": total, "list": roots}}


@router.post("/{slug:path}/comments")
async def comment_create(
    slug: str,
    body: CommentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """发表评论 / 回复（parent_id 指向根评论，最多两层）。"""
    _check_slug(slug)
    content = body.content.strip()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "评论内容不能为空")

    parent_id = None
    if body.parent_id is not None:
        parent = await db.get(Comment, body.parent_id)
        if parent is None or parent.slug != slug or parent.is_deleted:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "回复的评论不存在或已删除")
        # 只支持两层：回复的回复挂到根评论上
        parent_id = parent.parent_id or parent.id

    comment = Comment(user_id=user.id, slug=slug, parent_id=parent_id, content=content)
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "id": comment.id,
            "parent_id": comment.parent_id,
            "content": comment.content,
            "is_deleted": False,
            "created_at": comment.created_at.isoformat(),
            "user": _user_brief(user),
            "can_delete": True,
            "replies": [],
        },
    }


@router.delete("/comments/{comment_id}")
async def comment_delete(
    comment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """删除评论：作者本人或管理员；软删除，回复楼层数据保留。"""
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.is_deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "评论不存在")
    if comment.user_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "只能删除自己的评论")
    comment.is_deleted = True
    await db.commit()
    return {"code": 0, "message": "ok", "data": None}


# ---------------- 个人笔记（私有） ----------------


@router.get("/{slug:path}/note")
async def note_get(
    slug: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """读取当前用户在这篇文章上的笔记（无则返回 null）。"""
    _check_slug(slug)
    note = await db.scalar(select(Note).where(Note.user_id == user.id, Note.slug == slug))
    if note is None:
        return {"code": 0, "message": "ok", "data": None}
    return {"code": 0, "message": "ok", "data": {"content": note.content, "updated_at": note.updated_at.isoformat()}}


@router.put("/{slug:path}/note")
async def note_save(
    slug: str,
    body: NoteSaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """保存笔记（一篇文章一篇，整体覆盖）。"""
    _check_slug(slug)
    note = await db.scalar(select(Note).where(Note.user_id == user.id, Note.slug == slug))
    if note is None:
        note = Note(user_id=user.id, slug=slug, content=body.content)
        db.add(note)
    else:
        note.content = body.content
    await db.commit()
    await db.refresh(note)
    return {"code": 0, "message": "已保存", "data": {"content": note.content, "updated_at": note.updated_at.isoformat()}}


# ---------------- 个人中心 ----------------


@router.get("/my/overview")
async def my_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """个人中心统计：收藏数 / 笔记数 / 评论数。"""
    favorites = await db.scalar(select(func.count()).select_from(Favorite).where(Favorite.user_id == user.id)) or 0
    notes = await db.scalar(select(func.count()).select_from(Note).where(Note.user_id == user.id)) or 0
    comments = await db.scalar(
        select(func.count()).select_from(Comment).where(Comment.user_id == user.id, Comment.is_deleted.is_(False))
    ) or 0
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "favorites": favorites,
            "notes": notes,
            "comments": comments,
            "nickname": user.nickname,
            "avatar": user.avatar,
        },
    }


@router.get("/my/favorites")
async def my_favorites(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """我的收藏列表（slug + 收藏时间，标题由前端按内容索引解析）。"""
    result = await db.execute(
        select(Favorite.slug, Favorite.created_at)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    return {
        "code": 0,
        "message": "ok",
        "data": [{"slug": slug, "created_at": created_at.isoformat()} for slug, created_at in result.all()],
    }


@router.get("/my/notes")
async def my_notes(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """我的笔记列表（全部文章的私有笔记，含内容摘要）。"""
    result = await db.execute(
        select(Note.slug, Note.content, Note.updated_at)
        .where(Note.user_id == user.id)
        .order_by(Note.updated_at.desc())
    )
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {"slug": slug, "excerpt": (content or "").strip()[:120], "updated_at": updated_at.isoformat()}
            for slug, content, updated_at in result.all()
        ],
    }


@router.get("/my/comments")
async def my_comments(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """我的评论列表（未删除的，含所在文章 slug）。"""
    result = await db.execute(
        select(Comment.id, Comment.slug, Comment.content, Comment.created_at)
        .where(Comment.user_id == user.id, Comment.is_deleted.is_(False))
        .order_by(Comment.created_at.desc())
    )
    return {
        "code": 0,
        "message": "ok",
        "data": [
            {"id": cid, "slug": slug, "content": content, "created_at": created_at.isoformat()}
            for cid, slug, content, created_at in result.all()
        ],
    }
