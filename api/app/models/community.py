"""社区互动模型：文章收藏、点赞、评论、个人笔记。

设计要点：
- 一律以文章 slug 为关联键（与 view_logs 一致，文章本体是 Markdown 源文件，无 DB 主键）
- 收藏/点赞按 (user_id, slug) 唯一，天然防重复
- 评论支持一层回复（parent_id），软删除用 is_deleted 保留楼中楼数据完整性
- 笔记是用户私有数据，按 (user_id, slug) 唯一（一篇文章一篇笔记，PUT 覆盖式保存）
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Favorite(Base):
    """文章收藏：一个用户对一篇文章最多一条记录。"""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_user_slug_favorite"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Like(Base):
    """文章点赞：一个用户对一篇文章最多一条记录。"""

    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_user_slug_like"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Comment(Base):
    """文章评论：支持一层回复（parent_id 为空是根评论，否则指向根评论 id）。"""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # 纯文本，前端文本插值渲染防 XSS
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)  # 软删除：楼中楼引用保留
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Note(Base):
    """个人学习笔记（私有）：一篇文章一篇，PUT 整体覆盖保存。"""

    __tablename__ = "notes"
    __table_args__ = (UniqueConstraint("user_id", "slug", name="uq_user_slug_note"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
