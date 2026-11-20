"""认证依赖注入：实时校验（黑名单 + 版本号），管理员依赖。"""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.core.security import BL_KEY, VER_KEY, decode_token
from app.models.user import User, UserIdentity


async def get_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录或缺少凭证")
    return authorization[7:].strip()


async def get_current_user(
    token: Annotated[str, Depends(get_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """受保护接口统一入口：解码 → 黑名单 → 版本号 → 用户状态，任一步骤失败即 401。"""
    payload = decode_token(token, "access")
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证无效或已过期")

    redis = get_redis()
    user_id = int(payload["sub"])

    # 1. 单 token 黑名单（登出/封禁时写入）
    if await redis.get(BL_KEY.format(jti=payload["jti"])):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证已被吊销")

    # 2. 用户版本号比对（踢下线：所有旧 token 瞬时失效）
    current_ver = await redis.get(VER_KEY.format(user_id=user_id))
    if current_ver is None:
        # Redis 中无版本号（如重启丢数据），回源 DB 初始化
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
        await redis.set(VER_KEY.format(user_id=user_id), user.token_version)
        current_ver = str(user.token_version)
    if str(payload["ver"]) != str(current_ver):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证已失效，请重新登录")

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被封禁")
    return user


async def get_admin_user(user: Annotated[User, Depends(get_current_user)]) -> User:
    """管理端接口依赖：校验 role=admin。"""
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    return user


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    """可选登录：未带 token 或 token 无效时返回 None。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return await get_current_user(authorization[7:].strip(), db)
    except HTTPException:
        return None


async def find_user_by_identity(db: AsyncSession, provider: str, open_id: str) -> User | None:
    result = await db.execute(
        select(User)
        .join(UserIdentity, UserIdentity.user_id == User.id)
        .where(UserIdentity.provider == provider, UserIdentity.open_id == open_id)
    )
    return result.scalar_one_or_none()
