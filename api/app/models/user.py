"""数据模型：用户、第三方身份、站点设置、文章覆盖、阅读数。"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 管理员用账号密码登录；普通用户 username/password 为空
    username: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    nickname: Mapped[str] = mapped_column(String(64), default="")
    avatar: Mapped[str] = mapped_column(String(512), default="")
    role: Mapped[str] = mapped_column(String(16), default="user")  # user / admin
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    # 踢下线机制：签发 token 时写入 ver，踢下线/封禁时递增
    token_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserIdentity(Base):
    """第三方身份绑定：一个用户可绑定 github / gitee / sms 多种身份。"""

    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "open_id", name="uq_provider_openid"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(16), nullable=False)  # github / gitee / sms
    open_id: Mapped[str] = mapped_column(String(128), nullable=False)  # github/gitee 数字 id 或手机号
    union_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SiteSetting(Base):
    """站点设置键值表：后台可配，前台 SSR 读取（Redis 缓存 settings:site）。"""

    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 字符串
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ArticleOverride(Base):
    """文章展示覆盖：后台对 Markdown 源文件的展示细节覆盖（slug 关联，不改源文件）。"""

    __tablename__ = "article_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="published")  # draft / published
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    cover: Mapped[str] = mapped_column(String(512), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ViewLog(Base):
    """文章阅读数：按 slug 聚合。"""

    __tablename__ = "view_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
