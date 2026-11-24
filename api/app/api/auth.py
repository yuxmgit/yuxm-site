"""认证路由：短信验证码登录、管理员登录、OAuth 回调、刷新、登出与踢下线。"""
import math
import random

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import find_user_by_identity, get_current_user
from app.core.ratelimit import RateLimitError, check_sms_rate_limit
from app.core.redis_client import get_redis
from app.core.security import (
    BL_KEY,
    VER_KEY,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    blacklist_ttl,
    new_oauth_state,
    verify_password,
)
from app.models.user import User, UserIdentity

router = APIRouter(prefix="/auth", tags=["auth"])

SMS_CODE_KEY = "sms:code:{phone}"
STATE_KEY = "oauth:state:{state}"

OAUTH_CONFIG = {
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_url": "https://api.github.com/user",
        "client_id": "github_client_id",
        "client_secret": "github_client_secret",
        "redirect_uri": "github_redirect_uri",
        "scope": "read:user",
    },
    "gitee": {
        "authorize_url": "https://gitee.com/oauth/authorize",
        "token_url": "https://gitee.com/oauth/token",
        "user_url": "https://gitee.com/api/v5/user",
        "client_id": "gitee_client_id",
        "client_secret": "gitee_client_secret",
        "redirect_uri": "gitee_redirect_uri",
        "scope": "user_info",
    },
}


class SmsSendRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")


class SmsLoginRequest(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    code: str = Field(min_length=4, max_length=6)


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    """账号注册：用户名 3-32 位字母/数字/下划线，密码至少 8 位。"""

    username: str = Field(pattern=r"^[A-Za-z0-9_]{3,32}$")
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(default="", max_length=32)


class AccountLoginRequest(BaseModel):
    """普通用户密码登录（与管理员登录共用账号体系）。"""

    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    """个人资料更新：字段为 None 表示不修改；avatar 传空串表示清空。"""

    nickname: str | None = Field(default=None, max_length=32)
    avatar: str | None = Field(default=None, max_length=512)


class PasswordChangeRequest(BaseModel):
    """修改密码：已有密码时必须校验旧密码；SMS/OAuth 用户首次设置密码则免旧密码。"""

    old_password: str | None = None
    new_password: str = Field(min_length=8, max_length=64)


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


class RefreshRequest(BaseModel):
    refresh_token: str


def issue_token_pair(user: User) -> dict:
    """签发双 token（含 jti/ver）+ 用户信息。"""
    return {
        "access_token": create_access_token(user.id, user.token_version),
        "refresh_token": create_refresh_token(user.id, user.token_version),
        "user": {
            "id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "role": user.role,
            "has_password": bool(user.password_hash),
        },
    }


async def _ensure_ver(redis, user: User) -> None:
    """登录时初始化 Redis 版本号（幂等）。"""
    key = VER_KEY.format(user_id=user.id)
    if not await redis.exists(key):
        await redis.set(key, user.token_version)


# ---------------- 短信验证码 ----------------


def _send_sms(phone: str, code: str) -> None:
    """调用腾讯云 SMS；未配置密钥时降级为控制台输出（仅限开发环境）。"""
    if not settings.sms_secret_id:
        if settings.app_env != "dev":
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "短信服务未配置")
        print(f"[DEV-SMS] {phone} 验证码：{code}")
        return
    from tencentcloud.common import credential
    from tencentcloud.sms.v20210111 import client as sms_client, models as sms_models

    cred = credential.Credential(settings.sms_secret_id, settings.sms_secret_key)
    client = sms_client.SmsClient(cred, "ap-guangzhou")
    req = sms_models.SendSmsRequest()
    req.PhoneNumberSet = [f"+86{phone}"]
    req.SmsSdkAppId = settings.sms_app_id
    req.SignName = settings.sms_sign_name
    req.TemplateId = settings.sms_template_id
    req.TemplateParamSet = [code, str(settings.sms_code_expire_seconds // 60)]
    resp = client.SendSms(req)
    status_ = resp.SendStatusSet[0].Code
    if status_ != "Ok":
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"短信发送失败: {status_}")


@router.post("/sms/send")
async def sms_send(body: SmsSendRequest, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    try:
        await check_sms_rate_limit(redis, body.phone, ip, settings.sms_resend_interval_seconds)
    except RateLimitError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc

    code = f"{random.randint(0, 999999):06d}"
    await redis.set(SMS_CODE_KEY.format(phone=body.phone), code, ex=settings.sms_code_expire_seconds)
    # 开发模式（未配置 SMS 密钥）下把验证码回显给前端，方便本地联调；生产不会返回
    dev_mode = not settings.sms_secret_id and settings.app_env == "dev"
    _send_sms(body.phone, code)
    return {"code": 0, "message": "验证码已发送", "data": {"dev_code": code} if dev_mode else None}


@router.post("/sms/login")
async def sms_login(body: SmsLoginRequest, db: AsyncSession = Depends(get_db)) -> dict:
    redis = get_redis()
    key = SMS_CODE_KEY.format(phone=body.phone)
    saved = await redis.get(key)
    if not saved or saved != body.code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码错误或已过期")
    await redis.delete(key)

    user = await find_user_by_identity(db, "sms", body.phone)
    if user is None:
        user = User(nickname=f"用户{body.phone[-4:]}", phone=body.phone)
        db.add(user)
        await db.flush()
        db.add(UserIdentity(user_id=user.id, provider="sms", open_id=body.phone))
        await db.commit()
        await db.refresh(user)
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被封禁")
    await _ensure_ver(redis, user)
    return {"code": 0, "message": "ok", "data": issue_token_pair(user)}


# ---------------- 管理员登录 ----------------


@router.post("/admin/login")
async def admin_login(
    body: AdminLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    from sqlalchemy import select

    from app.core.login_guard import (
        LoginLockError,
        check_login_lock,
        clear_login_failures,
        record_login_failure,
    )

    redis = get_redis()
    ip = request.client.host if request.client else "unknown"

    # 1. 锁定检查前置：被锁定的请求在 bcrypt 校验前就被 O(1) 拒绝，防 CPU 打满
    try:
        await check_login_lock(redis, body.username, ip)
    except LoginLockError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        # 2. 失败计数：Lua 原子递增，第 3 次起每次再错锁定时间 +5 分钟
        await record_login_failure(redis, body.username, ip)
        # 统一错误信息，避免用户名枚举
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被封禁")

    # 3. 登录成功：清空失败计数
    await clear_login_failures(redis, body.username, ip)
    await _ensure_ver(redis, user)
    return {"code": 0, "message": "ok", "data": issue_token_pair(user)}


# ---------------- 账号注册 / 密码登录（普通用户） ----------------


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> dict:
    """开放注册：创建 role=user 账号并直接签发 token（注册即登录）。

    username 全局唯一（与管理员账号同一字段），password 仅存 bcrypt 哈希。
    """
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "用户名已被占用")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname or body.username,
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    redis = get_redis()
    await _ensure_ver(redis, user)
    return {"code": 0, "message": "注册成功", "data": issue_token_pair(user)}


@router.post("/login")
async def account_login(
    body: AccountLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """普通用户密码登录：与管理员登录相同的风控（锁定 + 失败计数），不限角色。"""
    from sqlalchemy import select

    from app.core.login_guard import (
        LoginLockError,
        check_login_lock,
        clear_login_failures,
        record_login_failure,
    )

    redis = get_redis()
    ip = request.client.host if request.client else "unknown"
    try:
        await check_login_lock(redis, body.username, ip)
    except LoginLockError as exc:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, str(exc)) from exc

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        await record_login_failure(redis, body.username, ip)
        # 统一错误信息，避免用户名枚举
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被封禁")

    await clear_login_failures(redis, body.username, ip)
    await _ensure_ver(redis, user)
    return {"code": 0, "message": "ok", "data": issue_token_pair(user)}


# ---------------- OAuth2（GitHub / Gitee） ----------------


@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(provider: str) -> dict:
    cfg = OAUTH_CONFIG.get(provider)
    if cfg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "不支持的登录方式")
    state = new_oauth_state()
    await get_redis().set(STATE_KEY.format(state=state), provider, ex=600)
    from urllib.parse import quote

    url = (
        f"{cfg['authorize_url']}?response_type=code"
        f"&client_id={settings.__getattribute__(cfg['client_id'])}"
        f"&redirect_uri={quote(settings.__getattribute__(cfg['redirect_uri']), safe='')}"
        f"&scope={quote(cfg['scope'], safe='')}"
        f"&state={state}"
    )
    return {"code": 0, "message": "ok", "data": {"authorize_url": url}}


async def _oauth_exchange(provider: str, code: str) -> dict:
    cfg = OAUTH_CONFIG[provider]
    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.__getattribute__(cfg["client_id"]),
                "client_secret": settings.__getattribute__(cfg["client_secret"]),
                "redirect_uri": settings.__getattribute__(cfg["redirect_uri"]),
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "OAuth 换取 token 失败")
        user_resp = await client.get(
            cfg["user_url"],
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        user_resp.raise_for_status()
        return user_resp.json()


@router.post("/oauth/{provider}/callback")
async def oauth_callback(provider: str, body: OAuthCallbackRequest, db: AsyncSession = Depends(get_db)) -> dict:
    cfg = OAUTH_CONFIG.get(provider)
    if cfg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "不支持的登录方式")

    redis = get_redis()
    state_key = STATE_KEY.format(state=body.state)
    saved_provider = await redis.get(state_key)
    if not saved_provider or saved_provider != provider:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "state 无效或已过期")
    await redis.delete(state_key)

    info = await _oauth_exchange(provider, body.code)
    open_id = str(info.get("id", ""))
    if not open_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "获取第三方用户信息失败")

    user = await find_user_by_identity(db, provider, open_id)
    if user is None:
        nickname = info.get("name") or info.get("login") or f"{provider}_{open_id}"
        avatar = info.get("avatar_url", "")
        user = User(nickname=nickname, avatar=avatar)
        db.add(user)
        await db.flush()
        db.add(UserIdentity(user_id=user.id, provider=provider, open_id=open_id))
        await db.commit()
        await db.refresh(user)
    if user.is_banned:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被封禁")
    await _ensure_ver(redis, user)
    return {"code": 0, "message": "ok", "data": issue_token_pair(user)}


# ---------------- Token 刷新 / 登出 / 踢下线 ----------------


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)) -> dict:
    redis = get_redis()
    payload = decode_token(body.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh token 无效")
    user_id = int(payload["sub"])

    if await redis.get(BL_KEY.format(jti=payload["jti"])):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh token 已被吊销")
    current_ver = await redis.get(VER_KEY.format(user_id=user_id))
    if current_ver is not None and str(payload["ver"]) != str(current_ver):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "凭证已失效，请重新登录")

    user = await db.get(User, user_id)
    if user is None or user.is_banned:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在或已被封禁")

    # 旋转：旧 refresh token 立即进黑名单
    await redis.set(BL_KEY.format(jti=payload["jti"]), 1, ex=blacklist_ttl(payload))
    await _ensure_ver(redis, user)
    return {"code": 0, "message": "ok", "data": issue_token_pair(user)}


@router.post("/logout")
async def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """登出：吊销当前 access token；可选传入 refresh token 一并吊销。"""
    auth_header = request.headers.get("authorization", "")
    payload = decode_token(auth_header[7:].strip(), "access")
    redis = get_redis()
    if payload:
        await redis.set(BL_KEY.format(jti=payload["jti"]), 1, ex=blacklist_ttl(payload))
    body = await request.json() if request.headers.get("content-length", "0") not in ("", "0") else {}
    refresh_token = body.get("refresh_token") if isinstance(body, dict) else None
    if refresh_token:
        rp = decode_token(refresh_token, "refresh")
        if rp:
            await redis.set(BL_KEY.format(jti=rp["jti"]), 1, ex=blacklist_ttl(rp))
    return {"code": 0, "message": "ok", "data": None}


@router.post("/logout-all")
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """退出所有设备（实时踢下线）：INCR 版本号，所有旧 token 瞬时失效。"""
    redis = get_redis()
    user.token_version += 1
    await db.commit()
    await redis.set(VER_KEY.format(user_id=user.id), user.token_version)
    return {"code": 0, "message": "已在所有设备退出登录", "data": None}


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict:
    return {"code": 0, "message": "ok", "data": issue_token_pair(user)["user"]}


# ---------------- 个人资料 / 修改密码 ----------------


@router.put("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """更新个人资料（昵称/头像 URL）。字段缺省不修改；avatar 传空串清空头像。"""
    if body.nickname is not None:
        nickname = body.nickname.strip()
        if not nickname:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "昵称不能为空")
        user.nickname = nickname
    if body.avatar is not None:
        user.avatar = body.avatar.strip()
    await db.commit()
    return {"code": 0, "message": "资料已更新", "data": issue_token_pair(user)["user"]}


@router.post("/password")
async def change_password(
    body: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """修改密码：已有密码校验旧密码；SMS/OAuth 用户首次设置免旧密码。"""
    if user.password_hash:
        if not body.old_password or not verify_password(body.old_password, user.password_hash):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "旧密码错误")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {
        "code": 0,
        "message": "已设置密码" if body.old_password is None else "密码已修改",
        "data": issue_token_pair(user)["user"],
    }
