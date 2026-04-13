"""运营配置：敏感词、黑名单、搜索同义词与灰度开关。"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, NVARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.datetime_utils import now_shanghai_naive


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class SensitiveWord(Base):
    __tablename__ = "sensitive_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class BlacklistWord(Base):
    __tablename__ = "blacklist_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    word: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False, unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class SearchSynonym(Base):
    __tablename__ = "search_synonyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    dst: Mapped[str] = mapped_column(NVARCHAR(64), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)


class SearchHotword(Base):
    __tablename__ = "search_hotwords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword: Mapped[str] = mapped_column(NVARCHAR(128), nullable=False, unique=True)
    cnt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_shanghai_naive)
