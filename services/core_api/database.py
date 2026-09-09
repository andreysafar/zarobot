"""
Zero Bot Core API — Database layer.
SQLite + SQLAlchemy async. Single source of truth for all platform data.
"""

import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    Numeric, func, select
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, selectinload
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/core_api/db.sqlite3")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relations
    balance = relationship("Balance", uselist=False, back_populates="user")
    ton_wallet = relationship("TonWallet", uselist=False, back_populates="user")
    bots = relationship("BotPassport", back_populates="owner")
    bug_reports = relationship("BugReport", back_populates="reporter")
    donations_sent = relationship("Donation", foreign_keys="Donation.from_user_id", back_populates="sender")
    donations_received = relationship("Donation", foreign_keys="Donation.to_user_id", back_populates="receiver")


class Balance(Base):
    """
    Баланс пользователя в звёздах.

    IAM здесь намеренно нет: он живёт в JSON-реестре IAMCoinService, который
    позже уедет в ончейн. Две копии одного баланса в разных хранилищах уже
    приводили к тому, что монеты списывались в одном месте, а начислялись
    в другом.
    """

    __tablename__ = "balances"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    stars = Column(Numeric(20, 9), default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="balance")


class TonWallet(Base):
    __tablename__ = "ton_wallets"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    address = Column(String(255), nullable=False, unique=True)
    public_key = Column(String(255), nullable=False)
    encrypted_private_key = Column(Text, nullable=False)  # encrypted at rest
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="ton_wallet")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # mint, burn, transfer, exchange, skill_purchase, donation
    from_currency = Column(String(20), nullable=True)
    to_currency = Column(String(20), nullable=True)
    from_amount = Column(Numeric(20, 9), default=0)
    to_amount = Column(Numeric(20, 9), default=0)
    rate = Column(Numeric(20, 9), default=1)
    tx_hash = Column(String(255), nullable=True)  # TON transaction hash
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    version = Column(String(20), default="1.0.0")
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator_telegram = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    category_icon = Column(String(10), nullable=True)
    price_ia_coins = Column(Numeric(20, 9), default=0)
    is_free = Column(Boolean, default=True)
    pricing_model = Column(String(20), default="one_time")  # one_time, subscription, freemium, pay_per_use
    revenue_creator_share = Column(Numeric(3, 2), default=0.60)
    revenue_platform_share = Column(Numeric(3, 2), default=0.30)
    revenue_telegram_share = Column(Numeric(3, 2), default=0.10)
    total_installations = Column(Integer, default=0)
    average_rating = Column(Float, default=0)
    ratings_count = Column(Integer, default=0)
    popularity_score = Column(Float, default=0)
    execution_type = Column(String(50), default="api_call")
    tags = Column(Text, default="[]")  # JSON array
    requirements = Column(Text, default="[]")  # JSON array
    config_schema = Column(Text, default="{}")  # JSON
    status = Column(String(20), default="active")  # active, deprecated, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SkillCategory(Base):
    __tablename__ = "skill_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    icon = Column(String(10), nullable=True)
    skills_count = Column(Integer, default=0)


class BotPassport(Base):
    __tablename__ = "bot_passports"

    id = Column(String(36), primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_telegram = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    personality = Column(String(100), default="ia")
    level = Column(Integer, default=0)
    xp = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active, sleeping, dead, listed
    nft_address = Column(String(255), nullable=True)
    container_id = Column(String(255), nullable=True)
    # Marketplace listing. The asking price used to be discarded on listing and
    # a hardcoded 50 charged on purchase, so it has to live somewhere.
    listing_price_ia_coins = Column(Numeric(20, 9), nullable=True)
    listing_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="bots")
    installed_skills = relationship("SkillInstallation", back_populates="bot")


class SkillInstallation(Base):
    __tablename__ = "skill_installations"

    id = Column(String(36), primary_key=True)
    skill_id = Column(String(36), ForeignKey("skills.id"), nullable=False)
    bot_id = Column(String(36), ForeignKey("bot_passports.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    price_paid = Column(Numeric(20, 9), default=0)
    config = Column(Text, default="{}")  # JSON
    installed_at = Column(DateTime, default=datetime.utcnow)

    bot = relationship("BotPassport", back_populates="installed_skills")


class BugReport(Base):
    __tablename__ = "bug_reports"

    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bot_id = Column(String(36), ForeignKey("bot_passports.id"), nullable=True)
    type = Column(String(20), default="error")  # error, feature, question
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    logs = Column(Text, nullable=True)
    screenshot_url = Column(String(500), nullable=True)
    status = Column(String(20), default="open")  # open, triaged, in_progress, resolved, closed
    priority = Column(String(20), default="medium")  # low, medium, high, critical
    assigned_to = Column(String(255), nullable=True)
    ai_analysis = Column(Text, nullable=True)  # Скрепка's analysis
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    reporter = relationship("User", back_populates="bug_reports")
    donations = relationship("Donation", back_populates="bug_report")


class Donation(Base):
    __tablename__ = "donations"

    id = Column(String(36), primary_key=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # to developer
    amount_ia_coins = Column(Numeric(20, 9), nullable=False)
    message = Column(Text, nullable=True)
    bug_report_id = Column(String(36), ForeignKey("bug_reports.id"), nullable=True)
    tx_hash = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship("User", foreign_keys=[from_user_id], back_populates="donations_sent")
    receiver = relationship("User", foreign_keys=[to_user_id], back_populates="donations_received")
    bug_report = relationship("BugReport", back_populates="donations")


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bot_id = Column(String(36), nullable=True, index=True)
    user_id = Column(Integer, nullable=True)
    error_type = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)
    traceback = Column(Text, nullable=True)
    context = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# Колонки, добавленные после того, как база уже могла быть создана.
# create_all создаёт только отсутствующие таблицы и не трогает существующие,
# поэтому у ранее заведённой БД новых колонок не появится, и запросы к ним
# упадут. Полноценные миграции — задача alembic; здесь минимум, чтобы
# существующая локальная база продолжала работать.
_ADDED_COLUMNS = {
    "bot_passports": {
        "listing_price_ia_coins": "NUMERIC",
        "listing_description": "TEXT",
    },
}


def _add_missing_columns(connection) -> None:
    """Досоздать недостающие колонки в уже существующих таблицах."""
    from sqlalchemy import inspect, text

    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())

    for table, columns in _ADDED_COLUMNS.items():
        if table not in existing_tables:
            continue
        present = {c["name"] for c in inspector.get_columns(table)}
        for column, sql_type in columns.items():
            if column in present:
                continue
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
            logger.info("Добавлена колонка {}.{}", table, column)


async def init_db():
    """Create all tables and seed default data."""
    # Ensure directory exists for SQLite
    db_path = Path("data/core_api")
    db_path.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_missing_columns)

    # Seed default data
    async with async_session() as session:
        # Default categories
        result = await session.execute(select(SkillCategory))
        if not result.scalars().all():
            categories = [
                SkillCategory(id=1, name="Разработка", icon="💻"),
                SkillCategory(id=2, name="Языки", icon="🌍"),
                SkillCategory(id=3, name="Анализ", icon="📊"),
                SkillCategory(id=4, name="Творчество", icon="🎨"),
                SkillCategory(id=5, name="Утилиты", icon="🛠️"),
            ]
            for cat in categories:
                session.add(cat)
            await session.commit()

        # Default skills
        result = await session.execute(select(Skill))
        if not result.scalars().all():
            skills = [
                Skill(
                    id="skill-001",
                    name="python-code-gen",
                    display_name="Генерация кода Python",
                    description="Автоматическая генерация кода на Python с использованием AI",
                    version="1.2.0",
                    creator_telegram="@ai_developer",
                    category="Разработка",
                    category_icon="💻",
                    price_ia_coins=Decimal("25"),
                    is_free=False,
                    total_installations=156,
                    average_rating=4.7,
                    ratings_count=23,
                    popularity_score=8.5,
                    tags=json.dumps(["python", "code", "ai", "development"]),
                    requirements=json.dumps(["Python 3.8+"]),
                    config_schema=json.dumps({"api_key": {"type": "string", "required": True}}),
                ),
                Skill(
                    id="skill-002",
                    name="smart-translator",
                    display_name="Умный переводчик",
                    description="Перевод текста между 50+ языками с контекстным пониманием",
                    version="2.0.1",
                    creator_telegram="@linguist_pro",
                    category="Языки",
                    category_icon="🌍",
                    price_ia_coins=Decimal("15"),
                    is_free=False,
                    total_installations=342,
                    average_rating=4.9,
                    ratings_count=45,
                    popularity_score=9.2,
                    tags=json.dumps(["translation", "languages", "nlp"]),
                    requirements=json.dumps([]),
                    config_schema=json.dumps({}),
                ),
                Skill(
                    id="skill-003",
                    name="sentiment-analysis",
                    display_name="Анализ настроения",
                    description="Определение эмоционального окраса текста",
                    version="1.0.0",
                    creator_telegram="@emotion_ai",
                    category="Анализ",
                    category_icon="📊",
                    price_ia_coins=Decimal("0"),
                    is_free=True,
                    total_installations=89,
                    average_rating=4.3,
                    ratings_count=12,
                    popularity_score=6.8,
                    tags=json.dumps(["sentiment", "emotion", "analysis", "free"]),
                    requirements=json.dumps([]),
                    config_schema=json.dumps({}),
                ),
                Skill(
                    id="skill-004",
                    name="weather-forecast",
                    display_name="Прогноз погоды",
                    description="Точный прогноз погоды для любого города мира",
                    version="1.1.0",
                    creator_telegram="@weather_dev",
                    category="Утилиты",
                    category_icon="🛠️",
                    price_ia_coins=Decimal("10"),
                    is_free=False,
                    total_installations=521,
                    average_rating=4.8,
                    ratings_count=67,
                    popularity_score=9.5,
                    tags=json.dumps(["weather", "forecast", "api"]),
                    requirements=json.dumps(["OpenWeatherMap API key"]),
                    config_schema=json.dumps({"api_key": {"type": "string", "required": True}}),
                ),
                Skill(
                    id="skill-005",
                    name="meme-generator",
                    display_name="Генератор мемов",
                    description="Создание мемов из текста и изображений",
                    version="1.0.0",
                    creator_telegram="@meme_master",
                    category="Творчество",
                    category_icon="🎨",
                    price_ia_coins=Decimal("20"),
                    is_free=False,
                    total_installations=203,
                    average_rating=4.5,
                    ratings_count=34,
                    popularity_score=7.9,
                    tags=json.dumps(["meme", "image", "creative", "fun"]),
                    requirements=json.dumps([]),
                    config_schema=json.dumps({"template": {"type": "string", "default": "default"}}),
                ),
            ]
            for skill in skills:
                session.add(skill)
            await session.commit()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_or_create_user(session: AsyncSession, telegram_id: int, username: str = None) -> User:
    """Get existing user or create new one with default balance."""
    result = await session.execute(
        select(User)
        .options(selectinload(User.balance))
        .where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, username=username)
        session.add(user)
        await session.flush()  # get user.id

        # Create default balance
        balance = Balance(user_id=user.id, stars=Decimal("0"))
        session.add(balance)
        await session.commit()

        # Re-fetch with balance loaded
        result = await session.execute(
            select(User)
            .options(selectinload(User.balance))
            .where(User.id == user.id)
        )
        user = result.scalar_one()

    return user
