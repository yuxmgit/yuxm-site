"""JWT 签发/校验（含 jti 与版本号）与密码哈希。

踢下线设计：
- access/refresh payload 均含 jti（uuid4）与 ver（签发时用户 token_version）
- 校验时先查 Redis 黑名单 auth:bl:{jti}，再比对 Redis auth:ver:{user_id}
- 登出：写 auth:bl:{jti}（TTL=剩余有效期）
- 退出所有设备：INCR auth:ver:{user_id}，旧 token 全部失效
"""
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VER_KEY = "auth:ver:{user_id}"
BL_KEY = "auth:bl:{jti}"


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


def _encode(payload: dict, expire_delta: timedelta) -> str:
    payload = {**payload, "exp": datetime.now(timezone.utc) + expire_delta}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int, ver: int) -> str:
    return _encode(
        {
            "sub": str(user_id),
            "jti": uuid.uuid4().hex,
            "ver": ver,
            "type": "access",
        },
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )


def create_refresh_token(user_id: int, ver: int) -> str:
    return _encode(
        {
            "sub": str(user_id),
            "jti": uuid.uuid4().hex,
            "ver": ver,
            "type": "refresh",
        },
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_token(token: str, expected_type: str = "access") -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    if not payload.get("jti") or "ver" not in payload or not payload.get("sub"):
        return None
    return payload


def blacklist_ttl(payload: dict) -> int:
    """黑名单 TTL = token 剩余秒数，避免无谓占用 Redis 内存。"""
    exp = payload.get("exp")
    if not exp:
        return 3600
    remain = int(exp - datetime.now(timezone.utc).timestamp())
    return max(remain, 1)


def new_oauth_state() -> str:
    """OAuth state：防 CSRF，一次性存 Redis。"""
    return secrets.token_urlsafe(24)
