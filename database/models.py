"""SQLAlchemy ORM 模型。

敏感字段（出生时间、出生地点）以加密密文形式存储，
见 v3.2 文档第 11 节数据安全与隐私。
"""

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    charts: Mapped[list["Chart"]] = relationship(back_populates="owner")


class Chart(Base):
    """命盘。出生时间/地点为加密字段。"""

    __tablename__ = "charts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    system: Mapped[str] = mapped_column(String(32))  # ziwei / bazi ...
    birth_datetime_enc: Mapped[str] = mapped_column(Text)  # 加密：出生时间
    birth_location_enc: Mapped[str | None] = mapped_column(Text, nullable=True)  # 加密：出生地
    chart_json: Mapped[dict] = mapped_column(JSON)  # 标准命盘 JSON（不含敏感字段）
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="charts")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="chart")


class Analysis(Base):
    """分析记录，关联 trace_id 便于全链路回溯。"""

    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chart_id: Mapped[int] = mapped_column(ForeignKey("charts.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    chart: Mapped[Chart] = relationship(back_populates="analyses")


class Feedback(Base):
    """用户反馈。入库前必须脱敏（见 v3.2 文档第 11 节）。"""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    analysis_id: Mapped[int | None] = mapped_column(ForeignKey("analysis.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    comment: Mapped[str] = mapped_column(Text)  # 已脱敏文本
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())