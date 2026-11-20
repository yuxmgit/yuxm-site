"""登录失败锁定：密码连续输错 3 次后锁定，此后每输错一次等待时间 +5 分钟。

高并发安全设计：
1. 计数与加时用 Redis Lua 脚本原子执行，消除"读-判断-写"竞态——
   并发请求不会互相覆盖计数，也不会漏加锁定时间
2. INCR 先递增后判断，天然防并发重复计数（两个并发请求 INCR 得到 3/4，
   不会都按 2 处理）
3. 锁定检查放在密码哈希校验（bcrypt，约百毫秒 CPU）之前：
   被锁定的请求用 Redis O(1) 直接拒绝，防止攻击者用并发请求打满服务器 CPU
4. 账号维度 + IP 维度双重计数：
   - 账号维度防止单账号被爆破
   - IP 维度防止攻击者遍历账号对同一出口 IP 发起分布式爆破
5. Redis 挂掉时选择"放行 + 记日志"而不是"全部拒绝"：
   锁定是降级保护手段，不能因为它的故障让正常用户无法登录
   （生产环境 Redis 与应用同机部署，故障概率极低）
"""
from redis.asyncio import Redis

LOGIN_FAIL_USER_KEY = "login:fail:user:{username}"
LOGIN_FAIL_IP_KEY = "login:fail:ip:{ip}"

# 账号维度：3 次开始锁定，每次再错 +5 分钟；计数窗口 15 分钟（内无失败则清零重来）
USER_LOCK_THRESHOLD = 3
USER_LOCK_STEP_SECONDS = 300
USER_COUNT_WINDOW_SECONDS = 900

# IP 维度：1 小时窗口内累计 30 次失败即锁该 IP 一小时（防换账号爆破）
IP_FAIL_THRESHOLD = 30
IP_WINDOW_SECONDS = 3600

# Lua：原子"递增 + 首次设窗口 TTL + 达到阈值后每次加时"。
# 返回当前失败次数。
_USER_LUA = """
local c = redis.call('INCR', KEYS[1])
if c == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
else
    if c >= tonumber(ARGV[2]) then
        local ttl = redis.call('TTL', KEYS[1])
        if ttl < 0 then
            ttl = tonumber(ARGV[1])
        end
        redis.call('EXPIRE', KEYS[1], ttl + tonumber(ARGV[3]))
    end
end
return c
"""

# Lua：IP 维度原子"递增 + 首次设窗口 TTL"。
_IP_LUA = """
local c = redis.call('INCR', KEYS[1])
if c == 1 then
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]))
end
return c
"""


class LoginLockError(Exception):
    """登录被锁定拒绝，message 面向用户展示（含剩余等待时间）。"""


def _fmt_wait(ttl: int) -> str:
    if ttl >= 60:
        return f"{(ttl + 59) // 60} 分钟"
    return f"{ttl} 秒"


async def check_login_lock(redis: Redis, username: str, ip: str) -> None:
    """登录前检查：账号或 IP 处于锁定状态则抛 LoginLockError（含剩余时间）。"""
    user_key = LOGIN_FAIL_USER_KEY.format(username=username)
    count = await redis.get(user_key)
    if count is not None and int(count) >= USER_LOCK_THRESHOLD:
        ttl = await redis.ttl(user_key)
        if ttl > 0:
            raise LoginLockError(f"密码错误次数过多，请 {_fmt_wait(ttl)} 后再试")

    ip_key = LOGIN_FAIL_IP_KEY.format(ip=ip)
    ip_count = await redis.get(ip_key)
    if ip_count is not None and int(ip_count) >= IP_FAIL_THRESHOLD:
        ttl = await redis.ttl(ip_key)
        if ttl > 0:
            raise LoginLockError(f"当前网络登录失败次数过多，请 {_fmt_wait(ttl)} 后再试")


async def record_login_failure(redis: Redis, username: str, ip: str) -> None:
    """密码校验失败后调用：原子递增计数，达到阈值即开始/延长锁定。"""
    await redis.eval(
        _USER_LUA,
        1,
        LOGIN_FAIL_USER_KEY.format(username=username),
        USER_COUNT_WINDOW_SECONDS,
        USER_LOCK_THRESHOLD,
        USER_LOCK_STEP_SECONDS,
    )
    await redis.eval(
        _IP_LUA,
        1,
        LOGIN_FAIL_IP_KEY.format(ip=ip),
        IP_WINDOW_SECONDS,
    )


async def clear_login_failures(redis: Redis, username: str, ip: str) -> None:
    """登录成功后调用：清除该账号与该 IP 的失败计数。"""
    await redis.delete(
        LOGIN_FAIL_USER_KEY.format(username=username),
        LOGIN_FAIL_IP_KEY.format(ip=ip),
    )
