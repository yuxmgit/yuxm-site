"""Redis 客户端：承载 JWT 黑名单/版本号、验证码、限频、站点设置缓存。

键设计约定（见 docs/release.md 与 auth 教程）：
- auth:ver:{user_id}    用户 token 版本号（踢下线 INCR）
- auth:bl:{jti}         单 token 黑名单，TTL=token 剩余有效期
- sms:code:{phone}      短信验证码
- ratelimit:*           限频计数
- settings:site         站点设置缓存
"""
import redis.asyncio as aioredis

from app.core.config import settings

_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            health_check_interval=30,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
