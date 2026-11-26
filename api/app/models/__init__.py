"""模型包统一入口：导入全部模型模块，保证 Base.metadata 注册完整。

main.py 的 dev 建表与运维脚本依赖这里的导入；新增模型模块必须在此追加。
"""
from app.models.article import Article  # noqa: F401
from app.models.community import Comment, Favorite, Like, Note  # noqa: F401
from app.models.user import ArticleOverride, SiteSetting, User, UserIdentity, ViewLog  # noqa: F401
