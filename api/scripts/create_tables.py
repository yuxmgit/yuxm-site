"""运维脚本：创建 Base.metadata 中缺失的数据表（幂等，只建缺失表，可安全重复执行）。

用法（把本文件 scp 到服务器任意路径后，在 deploy 目录执行）：
    sudo docker compose exec -T api python - < /tmp/create_tables.py

验证：
    sudo docker compose exec mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" yuxm_site -e "show tables"'

说明：
- 本脚本不进镜像（Dockerfile 只拷贝 app/ 与 alembic/），模型有变更、重新部署后执行一次即可
- create_all 只创建缺失的表，不会修改或删除已有表/数据
"""
import asyncio

from app.core.database import Base, engine
import app.models  # noqa: F401  导入以注册全部模型


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("create_all done")
    # 显式释放连接池：避免退出时 aiomysql 连接对象在事件循环关闭后
    # 被 GC 回收时报 "Event loop is closed"（无害但难看的清理警告）
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
