---
title: "第 11 章（实战）：JWT + Redis 黑名单 —— 从『登出无效』到『实时踢下线』"
description: "以本站（FastAPI + Redis）生产代码为素材，从入门到精通讲透 JWT 吊销难题：jti 黑名单、版本号踢下线、双 token 旋转、Lua 原子限流防爆破，附完整代码与高并发分析。"
category: jwt
series: sso-oauth-series
seriesOrder: 11
tags: ["JWT", "Redis", "踢下线", "限流", "高并发"]
date: 2026-11-19
sourceRepo: https://github.com/yuxiangming/yuxm-site
---

> 本站的**生产实现**就是这一章的活示例：登录 → 管理后台点"踢下线" → 前台下一秒 401 退出。所有代码均可在仓库 `api/app/core/` 下找到。
> 前置知识：第 3 章（Session 与 JWT）、第 7 章（安全攻防）。

## 11.1 从一个真实需求说起

JWT 最大的卖点——**无状态**——同时是它最大的软肋。服务端不存任何东西，意味着：

- 用户点"退出登录"，**旧 token 在过期前依然有效**（拿到它的人照样能调接口）
- 管理员想"把这个用户立刻踢下线"？做不到，只能等它自然过期

本站有三个功能都撞上了这堵墙：

1. 用户中心有"**退出所有设备**"按钮
2. 管理后台的用户管理页有"**踢下线**"按钮
3. 封禁用户时，他的所有已登录会话必须**立即失效**

这一章就沿着本站的真实演进路径，把这个问题从入门讲到精通。

## 11.2 入门：先看清 JWT 的校验流程

一个 JWT 由三段组成：`Header.Payload.Signature`。服务端校验只做一件事：

```python
payload = jwt.decode(token, secret, algorithms=["HS256"])
if payload["exp"] < now:
    return "过期"
return payload["sub"]  # 用户 ID
```

注意：**服务端没有查任何存储**。这就是"无状态校验"。它带来了横向扩展的便利（任何一台机器都能独立验签），也带来了吊销的难题——token 一旦签出去，在 `exp` 之前就是"真"的。

> **入门结论**：想让 token 可吊销，就必须让服务端校验时"多查一步存储"。所有吊销方案的本质，都是设计这一步查什么、怎么查。

## 11.3 方案演进：三种吊销思路的对比

| 方案 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| ① 超短过期时间 | access token 只给 5 分钟 | 零存储 | 5 分钟内照样有效；用户被迫频繁重新登录 |
| ② token 黑名单 | 登出时把 token 标记为无效，每次校验查一次 | 精确到单个 token | 多设备登录时要枚举该用户所有 token |
| ③ 用户版本号 | 每个 token 带签发时的"版本号"，校验时和最新版本比对 | 一次 `INCR` 废掉该用户全部 token | 无法精确吊销单个设备（除非每个设备一条版本号） |

**本站的答案是 ② + ③ 组合**：单设备登出用黑名单（精确），踢下线/退出所有设备/封禁用版本号（瞬时、全量）。两者都是 O(1) 的 Redis 操作。

## 11.4 实现一：payload 里埋 `jti` 和 `ver`

第一步是给每个 token 发"身份证"和"出厂批次号"。看本站 `api/app/core/security.py` 的签发代码：

```python
import uuid

VER_KEY = "auth:ver:{user_id}"    # 用户版本号：auth:ver:42
BL_KEY = "auth:bl:{jti}"          # token 黑名单：auth:bl:9f8e...

def create_access_token(user_id: int, ver: int) -> str:
    return _encode(
        {
            "sub": str(user_id),        # 用户 ID
            "jti": uuid.uuid4().hex,    # 本 token 的唯一身份证号
            "ver": ver,                 # 签发时刻该用户的版本号
            "type": "access",
        },
        timedelta(minutes=settings.jwt_access_expire_minutes),  # 15 分钟
    )
```

三个设计点：

- **`jti`（JWT ID）**：每个 token 唯一，是黑名单的 key。没有它，黑名单只能存整个 token 字符串——又长又浪费内存
- **`ver`（版本号）**：签发时从 DB/Redis 取该用户当前的 `token_version` 写死进 token。之后用户版本号再涨，旧 token 里的 `ver` 就"过时"了
- **黑名单 TTL = 剩余有效期**：登出只影响"还没过期"的时间段，过期后黑名单记录自动消失，**不泄漏内存**：

```python
def blacklist_ttl(payload: dict) -> int:
    """黑名单 TTL = token 剩余秒数，避免无谓占用 Redis 内存。"""
    exp = payload.get("exp")
    remain = int(exp - datetime.now(timezone.utc).timestamp())
    return max(remain, 1)
```

## 11.5 实现二：每请求校验管线（核心中的核心）

所有受保护接口共用一个 FastAPI 依赖注入，校验顺序就是一串"闸门"（`api/app/core/deps.py`）：

```python
async def get_current_user(token, db):
    payload = decode_token(token, "access")          # 闸门0：验签 + 过期 + 类型
    if payload is None:
        raise HTTPException(401, "凭证无效或已过期")

    redis = get_redis()
    user_id = int(payload["sub"])

    # 闸门1：单 token 黑名单（登出时写入）
    if await redis.get(BL_KEY.format(jti=payload["jti"])):
        raise HTTPException(401, "凭证已被吊销")

    # 闸门2：版本号比对（踢下线/封禁时递增）
    current_ver = await redis.get(VER_KEY.format(user_id=user_id))
    if current_ver is None:
        # Redis 无版本号（如重启丢数据）→ 回源 DB 重建
        user = await db.get(User, user_id)
        await redis.set(VER_KEY.format(user_id=user_id), user.token_version)
        current_ver = str(user.token_version)
    if str(payload["ver"]) != str(current_ver):
        raise HTTPException(401, "凭证已失效，请重新登录")

    # 闸门3：用户状态
    user = await db.get(User, user_id)
    if user.is_banned:
        raise HTTPException(403, "账号已被封禁")
    return user
```

**性能账本**：每请求额外开销 = 1~2 次 Redis GET（O(1)，亚毫秒）。版本号用"Redis 有就信 Redis，没有才回源 DB"的策略，正常运行时完全不碰 DB。

> **易错点**：黑名单查的必须是 `jti`，不是整个 token 字符串。存整个 token 每条要 500+ 字节，存 `jti` 只要 32 字节 hex，Redis 内存差一个数量级。

## 11.6 实现三：登出、退出所有设备、踢下线的代码

三个场景，三种写法（`api/app/api/auth.py`）：

**① 单设备登出**——只吊销当前这对 token：

```python
@router.post("/logout")
async def logout(user=Depends(get_current_user), ...):
    # access token 进黑名单
    await redis.set(BL_KEY.format(jti=payload["jti"]), 1, ex=blacklist_ttl(payload))
    # 请求体里带了 refresh token 就一并吊销
    if refresh_token:
        rp = decode_token(refresh_token, "refresh")
        await redis.set(BL_KEY.format(jti=rp["jti"]), 1, ex=blacklist_ttl(rp))
```

**② 退出所有设备（用户自己触发）**——一条 `INCR`：

```python
@router.post("/logout-all")
async def logout_all(user=Depends(get_current_user), db=Depends(get_db)):
    user.token_version += 1        # DB 版本号 +1（持久化）
    await db.commit()
    await redis.set(VER_KEY.format(user_id=user.id), user.token_version)
```

**③ 管理端踢下线 / 封禁**——复用同样的机制（`api/app/api/admin.py`）：

```python
user.token_version += 1
await db.commit()
await redis.set(VER_KEY.format(user_id=user.id), user.token_version)
if banned:
    user.is_banned = True
```

为什么"踢下线"不用黑名单枚举？设想用户在 5 台设备登录，黑名单方案要找出 5 个 token 的 `jti` 分别拉黑——但服务端根本没有地方存"这个用户签发过哪些 token"。版本号方案完全绕开了这个问题：**旧 token 里的 `ver` 是死的，新版本号是活的，一比就穿帮**。

## 11.7 进阶：双 token 旋转（refresh 也进黑名单）

只有 access/refresh 双 token 还不够——refresh token 有效期 7 天，泄露了照样灾难。本站在刷新时做了**旋转（rotation）**：

```python
@router.post("/refresh")
async def refresh(body: RefreshRequest, db=Depends(get_db)):
    payload = decode_token(body.refresh_token, "refresh")
    ...
    # 关键一行：旧 refresh token 立即进黑名单，每个只能用一次
    await redis.set(BL_KEY.format(jti=payload["jti"]), 1, ex=blacklist_ttl(payload))
    return issue_token_pair(user)
```

效果：即使 refresh token 被中间人截获，他用一次之后就失效了；合法用户下次刷新会被 401 踢回登录页，反而**暴露了攻击的存在**。这是 OAuth2 BCP（RFC 6749 安全最佳实践）推荐的方案。

## 11.8 精通：登录防爆破——高并发下为什么必须用 Lua

吊销解决的是"合法用户"，接下来防的是"非法请求"。管理员登录要求：**密码输错 3 次开始锁定，此后每输错一次 +5 分钟**。高并发场景下这个需求有个隐蔽的坑。

### 11.8.1 天真写法为什么在高并发下失效

```python
count = await redis.get(key)          # 读
if count >= 3:
    return "已锁定"
await redis.incr(key)                 # 写
if count >= 2:
    await redis.expire(key, ttl + 300)  # 加 5 分钟
```

三步之间都有间隙。推演一个并发场景：

```
两个并发请求 A、B 同时输错密码（用户双击了登录按钮）
A: GET count = 2   → 判断"未到 3 次，放行计数"
B: GET count = 2   → 也判断"未到 3 次"
A: INCR → 3
B: INCR → 4
A: expire(+300)
B: (count 读的是 2，没有加时)
```

结果：计数到了 4，但加时逻辑漏了一次——更严重的变体是**两个请求都读到 2、都认为没锁定**，攻击者用 100 个并发请求可以在锁定生效前打穿 N 次尝试。这就是典型的**"读-判断-写"竞态（check-then-act race）**。

### 11.8.2 本站解法：Lua 脚本原子执行（`api/app/core/login_guard.py`）

把"递增 + 首次设窗口 + 达到阈值后加时"压缩成 Redis 端的一段脚本，**执行期间不会插入任何其他命令**：

```lua
local c = redis.call('INCR', KEYS[1])          -- ① 原子递增
if c == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])     -- ② 首次失败才设计数窗口
else
    if c >= tonumber(ARGV[2]) then             -- ③ 第 3 次起
        local ttl = redis.call('TTL', KEYS[1])
        if ttl < 0 then ttl = tonumber(ARGV[1]) end
        redis.call('EXPIRE', KEYS[1], ttl + tonumber(ARGV[3]))  -- ④ 每次 +5 分钟
    end
end
return c
```

对应 Python 侧每次失败调用一次：

```python
await redis.eval(
    _USER_LUA, 1,
    LOGIN_FAIL_USER_KEY.format(username=username),
    USER_COUNT_WINDOW_SECONDS,   # 900：15 分钟计数窗口
    USER_LOCK_THRESHOLD,         # 3：第 3 次开始锁定
    USER_LOCK_STEP_SECONDS,      # 300：每次再错 +5 分钟
)
```

两个关键细节：

- **① 先 INCR 后判断**：两个并发请求分别拿到 3 和 4，永远不会"都按 2 处理"。`INCR` 本身是原子的，把判断建立在递增**结果**上，而不是递增**前**的旧值上——这是并发计数器的通用范式
- **② EXPIRE 只在 `c == 1` 时执行**：如果写在判断外面，每次失败都会重置 15 分钟窗口，"窗口内无失败自动清零"的语义就被破坏了

### 11.8.3 第二层防护：把 bcrypt 挡在门外

锁定检查必须放在**密码哈希校验之前**：

```python
# ① 先查锁：被锁的请求在这里就被 O(1) 拒绝
try:
    await check_login_lock(redis, body.username, ip)
except LoginLockError as exc:
    raise HTTPException(429, str(exc))          # "请 X 分钟后再试"

# ② 然后才做昂贵的 bcrypt 校验（约 100ms CPU）
if not verify_password(body.password, user.password_hash):
    await record_login_failure(redis, body.username, ip)
    raise HTTPException(401, "用户名或密码错误")
```

为什么顺序重要？bcrypt 的设计目标就是"慢"（单次约 100ms CPU）。如果先验密码再查锁，攻击者锁定生效前每秒可发起几十个并发请求，**每个都消耗一次 bcrypt**，几百个并发就能把 2C 的 CPU 打满——登录锁变成了"CPU 放大攻击"。前置检查后，被锁请求只消耗一次 Redis GET，成本差 4 个数量级。

### 11.8.4 账号 + IP 双维度

只按账号锁定有个漏洞：攻击者拿到一份用户名列表，对**每个账号只错 2 次**（永远不触发阈值），就能分布式爆破。所以本站同时维护一个 IP 维度计数器（1 小时 30 次失败锁 IP 一小时）。注意 IP 计数器不需要 Lua 加时逻辑——它是"累计达阈值即锁"，普通 `INCR` 就够，这是**按需选择原子性强度**的例子。

## 11.9 配套：OAuth2 的 state 与统一错误格式

OAuth2 授权码流程里，`state` 参数是防 CSRF 的标准手段，本站实现和登录锁定共用同一套 Redis 原子思想：

```python
# 发起授权：生成一次性 state，10 分钟过期
state = secrets.token_urlsafe(24)
await redis.set(f"oauth:state:{state}", provider, ex=600)

# 回调：校验后立即删除（一次性）
saved = await redis.get(state_key)
if not saved or saved != provider:
    raise HTTPException(400, "state 无效或已过期")
await redis.delete(state_key)
```

不删的话，同一个 state 可以被重放给回调接口——"用后即焚"和验证码删除是同一个模式。

另外，所有这些业务提示（"请 X 分钟后再试"）要能到达前端，后端需要统一异常格式。FastAPI 默认返回 `{"detail": "..."}`，本站在 `main.py` 加了一个 handler 转成 `{"code": 429, "message": "..."}`，前端 `catch (e) { showError(e.data.message) }` 一行就够了。

## 11.10 验证：手把手复现"踢下线"

```bash
# 1. 管理员登录，拿 token
curl -s -X POST http://localhost:8000/api/auth/admin/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"yuxiangming","password":"yuxiangming"}'
# 记下 data.access_token，设为 TOKEN

# 2. 正常访问受保护接口
curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
# → {"code":0, "data":{"role":"admin",...}}

# 3. 退出所有设备（INCR 版本号）
curl -s -X POST http://localhost:8000/api/auth/logout-all -H "Authorization: Bearer $TOKEN"

# 4. 同一个 token 再访问 → 立即 401
curl -s http://localhost:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
# → {"code":401, "message":"凭证已失效，请重新登录"}
```

密码锁定可以直接压测复现：连续输错 3 次密码，第 4 次请求返回 `429 {"message":"密码错误次数过多，请 5 分钟后再试"}`，再错一次等待时间变 10 分钟。

## 11.11 生产思考与面试题

**这套方案的性能边界**：

- 每请求新增开销：1~2 次 Redis GET + 1 次 DB `get(User)`（可再加一层用户缓存）。对比 Session 方案的"每次查存储"其实打平，但保留了 JWT 的验签扩展性
- Redis 单实例每秒 10 万+ 次 GET，踢下线的 `INCR` 更是瞬时操作——**这不是瓶颈**
- 真正要规划的是 Redis 高可用：版本号 key 丢失会被"回源 DB 重建"兜底（11.5 的 `current_ver is None` 分支），所以 Redis 短暂宕机最多损失"踢下线能力"，不会导致用户被误踢

**面试题清单**：

1. JWT 无状态，为什么还需要黑名单？——吊销与踢下线需求（11.1）
2. 黑名单和版本号方案怎么选？——精确吊销 vs 全量失效，组合使用（11.3）
3. 黑名单的 TTL 为什么要设成 token 剩余有效期？——内存自动回收（11.4）
4. 高并发下 `GET → 判断 → INCR` 有什么问题？——check-then-act 竞态，用 Lua/先 INCR 后判断解决（11.8）
5. 为什么登录锁定检查要放在 bcrypt 之前？——bcrypt 是 CPU 放大器，防资源耗尽（11.8.3）
6. refresh token 旋转防什么？——token 重放，泄露后一次即废（11.7）
7. OAuth2 的 state 防什么？怎么实现？——CSRF，一次性随机串 + 用后即焚（11.9）
8. Redis 挂了这套认证会怎样？——回源 DB 重建版本号，降级不雪崩（11.5）

**一句话总结**：无状态是 JWT 的卖点，也是它的天花板；用 `jti` 黑名单保精度、用版本号保实时、用 Lua 原子保并发、用前置检查保 CPU——四件套齐了，JWT 才算"生产可用"。本站源码（`api/app/core/security.py`、`deps.py`、`login_guard.py`、`ratelimit.py`）就是这套方案的最小完整实现。
