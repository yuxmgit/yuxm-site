"""初始化种子数据：创建管理员账号（yuxiangming / yuxiangming）与默认站点设置。

用法：python -m app.seed
生产上线后请立即在后台修改密码。
"""
import asyncio
import json

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.security import hash_password
from app.models.user import SiteSetting, User

DEFAULT_SETTINGS = {
    "site_name": "虞先森的技术站",
    "seo_description": "技术教程站：Redis 集群、MySQL 主从、Jenkins、Docker、JWT、OAuth2、Python 框架实战。",
    "hero_intro": "写教程，也在跑教程。本站自身架构即教程的最佳示例：Nuxt3 + FastAPI + Redis 黑名单踢下线 + Docker + Jenkins。",
    "announcement": "",
    "icp": "",
    "github_url": "https://github.com/yuxiangming",
    "gitee_url": "https://gitee.com/yuxiangming",
}


async def seed() -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.username == settings.admin_init_username))
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                username=settings.admin_init_username,
                password_hash=hash_password(settings.admin_init_password),
                nickname="管理员",
                role="admin",
            )
            db.add(admin)
            print(f"已创建管理员账号：{settings.admin_init_username}（上线后请立即修改密码）")
        else:
            print("管理员账号已存在，跳过")

        for key, value in DEFAULT_SETTINGS.items():
            exists = await db.execute(select(SiteSetting).where(SiteSetting.key == key))
            if exists.scalar_one_or_none() is None:
                db.add(SiteSetting(key=key, value=json.dumps(value, ensure_ascii=False)))
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
