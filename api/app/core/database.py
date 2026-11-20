"""MySQL 异步引擎与会话。"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 注意：不用 pool_pre_ping——SQLAlchemy 的 aiomysql 方言 ping() 签名不匹配会抛
# TypeError（AsyncAdapt_aiomysql_connection.ping missing 'reconnect'），
# 失效连接由 pool_recycle 兜底回收
engine = create_async_engine(settings.mysql_url, pool_recycle=3600)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
