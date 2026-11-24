---
title: "第 2 章：JWT 怎么把人踢下线——黑名单与版本号的双保险"
description: "0 基础向：JWT 生下来就改不了的缺陷怎么补？本站真实代码逐行拆解：jti 黑名单、token_version 版本号、Redis TTL 精确对齐，管理员点一下踢人为什么下一秒生效。"
category: jwt
series: auth-state-lab
seriesOrder: 2
tags: ["JWT", "踢下线", "Redis 黑名单", "版本号", "0基础"]
date: 2026-11-24
sourceRepo: https://github.com/yuxiangming/yuxm-site
---

> 「登录状态与踢下线·0 基础」系列第 2 章。上一章说到：JWT 是防伪签名卡片，但卡片在有效期内无法作废。这一章讲本站怎么用 Redis 给 JWT 装上"作废开关"。

## 1. 先搞懂 JWT 卡片上写了什么

一个 JWT 长这样（中间用点隔开的三段）：

```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIiwidmVyIjoxLCJqdGkiOiJhYmMxMjMifQ.SflKxwRJSmeM...
```

把中间那段解开（它只是 Base64 编码，不是加密！），就是一张登记卡：

```json
{
  "sub": "1",        <- 用户 ID：我是 1 号用户
  "ver": 1,          <- 版本号：我签发时用户处于第 1 代凭证期
  "jti": "abc123",   <- 卡片身份证号：每张卡唯一
  "exp": 1795502883  <- 过期时间戳
}
```

**关键认知：这张卡一旦签发，字就印死了。** 用户不能改（签名会碎），服务器也不能改——它不在服务器手里。所以"踢人"不可能靠改卡片，只能靠**外部台账**。台账放在哪？上一章的答案：Redis。

## 2. 双 token：为什么要两张卡？

本站签发的是一对 token（`api/app/api/auth.py`）：

| 卡 | 有效期 | 用途 |
|---|---|---|
| access_token | 短（30 分钟级） | 每次请求都出示，丢了损失小 |
| refresh_token | 长（7 天级） | 只用来换新卡对，平时锁在抽屉里 |

为什么两张？如果只有一张长效卡，它被偷了，攻击者能用 7 天。两张卡的设计里，天天见人的卡短命，即使被偷，30 分钟自动失效；而换卡通道（refresh）是服务器完全掌控的——想关随时能关。**这本身就是第一层"被动踢人"：别管什么机制，反正 30 分钟后肯定失效。**

但 30 分钟对"管理员踢恶意用户"来说太慢了。主动踢人靠下面两件武器。

## 3. 武器一：jti 黑名单——作废"某一张卡"

每张 access token 都有唯一身份证号 `jti`。用户登出时，服务器把这张卡的 jti 写进 Redis 黑名单：

```python
# api/app/api/auth.py  登出逻辑（节选）
payload = decode_token(token, "access")
await redis.set(
    BL_KEY.format(jti=payload["jti"]),   # 键：黑名单:abc123
    1,
    ex=blacklist_ttl(payload),           # 过期时间 = 卡片剩余寿命
)
```

之后每个受保护请求都会先查一下（`api/app/core/deps.py`）：

```python
# 1. 单 token 黑名单（登出/封禁时写入）
if await redis.get(BL_KEY.format(jti=payload["jti"])):
    raise HTTPException(401, "凭证已被吊销")
```

**一个细节见功力**：黑名单的过期时间不是随便设的，而是精确对齐"这张卡还剩多久到期"。卡片 10 分钟后本来就要过期了，黑名单就只记 10 分钟——过期后 Redis 自动清掉，黑名单永远不会无限膨胀。**用 Redis 的 TTL 替代了定时清理任务，这是 Redis 作为状态保管箱的经典用法。**

局限：黑名单是"按张作废"，只能封掉**一张**卡。用户有手机+电脑两张卡呢？一个个记太笨了。于是有了武器二。
## 4. 武器二：token_version 版本号——作废"一个人"的所有卡

思路换个维度：黑名单盯"卡"，版本号盯"人"。每个用户身上挂一个版本号（`users.token_version`），签发每张卡时把当时的版本号印上去（就是卡片里的 `ver` 字段）。

"踢人下线"（退出所有设备）的实现只有三行：

```python
# api/app/api/auth.py  POST /auth/logout-all
user.token_version += 1          # 3 -> 4：此人所有旧卡瞬间过时
await db.commit()
await redis.set(VER_KEY.format(user_id=user.id), user.token_version)  # Redis 同步新版本
```

之后任何旧卡来访问，对不上号：

```python
# api/app/core/deps.py
current_ver = await redis.get(VER_KEY.format(user_id=user_id))  # Redis 里是 4
if str(payload["ver"]) != str(current_ver):                      # 卡上印的是 3
    raise HTTPException(401, "凭证已失效，请重新登录")
```

**为什么叫"下一秒生效"？** 因为不需要等卡片到期，也不需要逐张拉黑——版本号一变，旧卡在这个用户下一次请求的瞬间就死了。管理员在后台点"踢下线" -> 版本号 +1 -> 那位用户刷新页面立刻 401，这就是本站真实的链路。

### 三个机制各司其职

| 机制 | 挂在哪 | 作废粒度 | 典型场景 |
|---|---|---|---|
| exp 过期时间 | 卡片本身 | 一张卡（被动） | 兜底：无论如何 30 分钟后失效 |
| jti 黑名单 | Redis（带 TTL） | 一张卡（主动） | 登出当前设备 |
| token_version | Redis + DB | **一个人**的全部卡 | 管理员踢人、退出所有设备、封禁 |

## 5. Redis 挂了怎么办？——降级与回源

把所有状态都放 Redis，Redis 就成了关键依赖。本站做了两手准备：

**第一手：版本号回源。** Redis 重启导致版本号丢失时，并不直接判死：

```python
# api/app/core/deps.py
current_ver = await redis.get(VER_KEY.format(user_id=user_id))
if current_ver is None:
    # Redis 中无版本号（如重启丢数据），回源 DB 初始化
    user = await db.get(User, user_id)
    await redis.set(VER_KEY.format(user_id=user_id), user.token_version)
    current_ver = str(user.token_version)
```

数据库里存着权威版本号，Redis 只是它的缓存视图——丢了就从 DB 捞回来重建。

**第二手：登录时幂等初始化。** 每次登录都调 `_ensure_ver()`：Redis 里没有版本号才写，有就不动。保证任何一条路径进来，版本号都能自愈。

这也回答了上一章埋的问题：**JWT + Redis 的组合里，JWT 负责"验明正身"（免查数据库），Redis 负责"掌管生死"（黑名单/版本号），数据库负责"最终真相"（版本号的持久源头）。** 三层各管一段，谁也不是单点。

## 6. 自己动手验证（5 分钟）

本站的踢下线全流程可以这样亲眼看一遍：

1. 浏览器 A 登录站点（拿到 token 对）
2. 再开浏览器 B（或无痕窗口）登录同一账号
3. 在 B 里点头像 -> 「退出所有设备」
4. 回到 A，随便点一个需要登录的操作 -> **立刻 401，要求重新登录**

A 的卡片签名完全合法、远未过期，但版本号已经对不上了——这就是"卡片有效但台账作废"的实战效果。

## 7. 小结

```
踢人 = 让"合法的卡"作废
  |- 按卡踢：jti 黑名单（Redis SET + TTL 对齐剩余寿命）
  |- 按人踢：token_version（Redis + DB 双写，INCR 即全下线）
  |- 依赖 Redis 挂了怎么办：版本号回源 DB，登录幂等重建
```

Redis 这么重要，那它自己挂了、断电了、数据丢了怎么办？「可靠性」问题请转到姊妹系列：[Redis 可靠性与集群实录](/posts/redis-cluster/redis-reliability-101)——从持久化一路讲到 3 主 3 从集群的故障转移实录。