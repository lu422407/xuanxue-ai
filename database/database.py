"""数据库连接管理。

默认使用 PostgreSQL（生产），测试环境可用 SQLite 内存库。
连接串从环境变量 DATABASE_URL 读取。
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://xuanxue:xuanxue@localhost:5432/xuanxue",
    )


def create_db_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


SessionLocal = sessionmaker(bind=create_db_engine(), autoflush=False)


def init_db():
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=create_db_engine())