"""在线文章模型：后台新建/编辑的文章正文入库，与 content/ 目录静态文章并行。

URL 约定：slug 即文章完整路径（如 blog/hello-world），前台路由 /posts/{slug} 优先查库。
"""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import utcnow


class Article(Base):
    """后台在线文章：即编即发，无需重新构建前端镜像。"""

    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("slug", name="uq_article_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(256), nullable=False, index=True)  # 完整路径，如 blog/hello
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(String(512), default="")
    category: Mapped[str] = mapped_column(String(32), default="docker")  # 与 CATEGORIES 键一致
    tags: Mapped[str] = mapped_column(String(512), default="")  # 逗号分隔
    date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 展示日期
    series: Mapped[str] = mapped_column(String(64), default="")
    series_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_repo: Mapped[str] = mapped_column(String(512), default="")
    content_md: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown 正文
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft / published
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
