"""限频器：验证码接口防刷（IP + 手机号双重限频，Redis 计数实现）。

策略：
- 手机号：60 秒 1 次（发送间隔）、每天 10 次
- IP：每小时 10 次、每天 50 次
超出任何一条即拒绝，防止短信轰炸与费用刷爆。
"""
from redis.asyncio import Redis

SMS_INTERVAL_KEY = "ratelimit:sms:interval:{phone}"
SMS_PHONE_DAY_KEY = "ratelimit:sms:phone:day:{phone}"
SMS_IP_HOUR_KEY = "ratelimit:sms:ip:hour:{ip}"
SMS_IP_DAY_KEY = "ratelimit:sms:ip:day:{ip}"

PHONE_DAY_LIMIT = 10
IP_HOUR_LIMIT = 10
IP_DAY_LIMIT = 50

DAY_SECONDS = 86400
HOUR_SECONDS = 3600


class RateLimitError(Exception):
    """限频拒绝，message 面向用户展示。"""


async def check_sms_rate_limit(redis: Redis, phone: str, ip: str, interval_seconds: int) -> None:
    """发送验证码前的限频检查，通过则落计数，不通过抛 RateLimitError。"""
    interval_key = SMS_INTERVAL_KEY.format(phone=phone)
    if await redis.exists(interval_key):
        ttl = await redis.ttl(interval_key)
        raise RateLimitError(f"发送过于频繁，请 {max(ttl, 1)} 秒后再试")

    phone_day = SMS_PHONE_DAY_KEY.format(phone=phone)
    if int(await redis.get(phone_day) or 0) >= PHONE_DAY_LIMIT:
        raise RateLimitError("该手机号今日发送次数已达上限")

    ip_hour = SMS_IP_HOUR_KEY.format(ip=ip)
    if int(await redis.get(ip_hour) or 0) >= IP_HOUR_LIMIT:
        raise RateLimitError("当前网络发送过于频繁，请稍后再试")

    ip_day = SMS_IP_DAY_KEY.format(ip=ip)
    if int(await redis.get(ip_day) or 0) >= IP_DAY_LIMIT:
        raise RateLimitError("当前网络今日发送次数已达上限")

    pipe = redis.pipeline()
    pipe.set(interval_key, 1, ex=interval_seconds)
    pipe.incr(phone_day)
    pipe.expire(phone_day, DAY_SECONDS)
    pipe.incr(ip_hour)
    pipe.expire(ip_hour, HOUR_SECONDS)
    pipe.incr(ip_day)
    pipe.expire(ip_day, DAY_SECONDS)
    await pipe.execute()
