"""应用配置：全部敏感项来自环境变量 / .env，禁止硬编码。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "yuxm"
    mysql_password: str = ""
    mysql_database: str = "yuxm_site"

    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_password: str = ""
    redis_db: int = 0

    # JWT
    jwt_secret: str = "dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7

    # 管理员种子账号
    admin_init_username: str = "yuxiangming"
    admin_init_password: str = "yuxiangming"

    # 腾讯云 SMS
    sms_secret_id: str = ""
    sms_secret_key: str = ""
    sms_app_id: str = ""
    sms_sign_name: str = ""
    sms_template_id: str = ""
    sms_code_expire_seconds: int = 300
    sms_resend_interval_seconds: int = 60

    # OAuth
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/server/auth/github/callback"
    gitee_client_id: str = ""
    gitee_client_secret: str = ""
    gitee_redirect_uri: str = "http://localhost:3000/server/auth/gitee/callback"

    @property
    def mysql_url(self) -> str:
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
