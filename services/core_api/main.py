"""
Zero Bot Core API — FastAPI backend.
All data in SQLite via SQLAlchemy async. No JSON files.
"""

import json
import os
import secrets
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import (
    init_db, get_session, get_or_create_user, async_session,
    User, Balance, TonWallet, Transaction, Skill, SkillCategory,
    BotPassport, SkillInstallation, BugReport, Donation, ErrorLog,
)
from iam_coin import IAMCoinService, wallet_for
from secrets_store import EncryptionUnavailable, decrypt_secret, encrypt_secret, is_configured

app = FastAPI(title="Zero Bot Core API", version="2.0.0")

# Shared secret for service-to-service calls. This API moves balances and
# transfers bot ownership, so it must never run open.
CORE_API_TOKEN = os.getenv("CORE_API_TOKEN", "")
AUTH_HEADER = "X-Core-API-Token"

# Paths reachable without the token: liveness only.
PUBLIC_PATHS = {"/health"}

# Browsers are not a client here - the callers are other containers. An empty
# list means no cross-origin access, which is the right default for this API.
CORS_ORIGINS = [o for o in os.getenv("CORE_API_CORS_ORIGINS", "").split(",") if o]


@app.middleware("http")
async def require_token(request, call_next):
    """
    Authenticate every request except /health.

    Applied as middleware rather than a per-route dependency on purpose: a new
    endpoint is protected by default instead of being protected only if someone
    remembers to add the dependency.
    """
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    if not CORE_API_TOKEN:
        # Fail closed. A missing variable must not silently reopen the API.
        return JSONResponse(
            status_code=503,
            content={"detail": "CORE_API_TOKEN is not configured; refusing to serve."},
        )

    provided = request.headers.get(AUTH_HEADER, "")
    # compare_digest keeps the check constant-time.
    if not secrets.compare_digest(provided, CORE_API_TOKEN):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=bool(CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)

iam_coin = IAMCoinService()

# Exchange rates - the server-side source of truth. The converted amount is
# always computed here and never taken from the request: `to_amount` and `rate`
# arrive from a client and treating them as authoritative would let a caller
# turn one Star into any number of IA-Coins.
RATE_STARS_TO_IA = Decimal("0.01")
RATE_IA_TO_STARS = Decimal("100")

# Доля продавца при продаже бота. Остаток забирает казна реестра
# (platform_treasury) — отдельный счёт платформы в SQLite для этого не нужен.
SELLER_SHARE = Decimal("0.6")


# ═══════════════════════════════════════════
# Pydantic schemas
# ═══════════════════════════════════════════

class ExchangeRatesResponse(BaseModel):
    stars_to_ia_coin: float = float(RATE_STARS_TO_IA)
    ia_coin_to_stars: float = float(RATE_IA_TO_STARS)


class BalanceResponse(BaseModel):
    stars: str
    ia_coins: str


class ExchangeRequest(BaseModel):
    user_id: int
    from_currency: str
    to_currency: str
    from_amount: float
    # Accepted for backwards compatibility with existing clients, but ignored:
    # the server recomputes both from its own rates.
    to_amount: Optional[float] = None
    rate: Optional[float] = None


class SkillInstallRequest(BaseModel):
    bot_passport_id: str
    # Кто ставит навык. Без этого поля сервер не знал заказчика и безусловно
    # списывал с владельца бота: любой, кто знает id бота, мог ставить платные
    # навыки за чужой счёт.
    user_id: int
    config: dict = {}


class BotPassportCreate(BaseModel):
    owner_id: int
    owner_telegram: str = ""
    name: str
    personality: str = "ia"


class BugReportCreate(BaseModel):
    user_id: int
    bot_id: Optional[str] = None
    type: str = "error"
    title: str
    description: str
    logs: Optional[str] = None


class DonationCreate(BaseModel):
    from_user_id: int
    to_user_id: Optional[int] = None
    amount_ia_coins: float
    message: Optional[str] = None
    bug_report_id: Optional[str] = None


class ErrorLogCreate(BaseModel):
    bot_id: Optional[str] = None
    user_id: Optional[int] = None
    error_type: Optional[str] = None
    message: str
    traceback: Optional[str] = None
    context: Optional[dict] = None


# ═══════════════════════════════════════════
# Startup / Shutdown
# ═══════════════════════════════════════════

@app.on_event("startup")
async def startup():
    await init_db()
    if not is_configured():
        logger.warning(
            "WALLET_ENCRYPTION_KEY не задан — операции с TON-кошельками "
            "будут отклоняться (503). Остальной API работает."
        )
    # Seed default categories if empty. Use the sessionmaker from database.py:
    # app.state.db_session_maker was never assigned, so this raised
    # AttributeError and the API could not start at all.
    async with async_session() as session:
        result = await session.execute(select(SkillCategory))
        if not result.scalars().all():
            defaults = [
                SkillCategory(id=1, name="Разработка", icon="💻"),
                SkillCategory(id=2, name="Языки", icon="🌍"),
                SkillCategory(id=3, name="Анализ", icon="📊"),
                SkillCategory(id=4, name="Творчество", icon="🎨"),
                SkillCategory(id=5, name="Утилиты", icon="🛠️"),
            ]
            for cat in defaults:
                session.add(cat)
            await session.commit()


@app.on_event("shutdown")
async def shutdown():
    pass


# ═══════════════════════════════════════════
# Health
# ═══════════════════════════════════════════

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "zero-bot-core-api",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ═══════════════════════════════════════════
# Platform Stats
# ═══════════════════════════════════════════

@app.get("/api/v1/stats/")
async def get_platform_stats(session: AsyncSession = Depends(get_session)):
    users_count = await session.execute(select(User))
    bots_count = await session.execute(select(BotPassport))
    skills_count = await session.execute(select(Skill))
    tx_count = await session.execute(select(Transaction))

    return {
        "total_bots": len(bots_count.scalars().all()),
        "total_users": len(users_count.scalars().all()),
        "total_skills": len(skills_count.scalars().all()),
        "total_personalities": 1,
        "nft_passports": len(bots_count.scalars().all()),
        "trading_volume": len(tx_count.scalars().all()),
        "new_bots_24h": 0,
        "messages_24h": 0,
        "transactions_24h": 0,
    }


# ═══════════════════════════════════════════
# Users & Balances
# ═══════════════════════════════════════════

async def load_balance(session: AsyncSession, user_id: int) -> Optional[Balance]:
    """
    Load a user's balance by primary key.

    `User.balance` is a lazy relationship, and touching it on an AsyncSession
    does IO outside the greenlet context - that raises MissingGreenlet and
    breaks the endpoint. Balance is keyed by user_id, so a direct get() avoids
    the relationship entirely.
    """
    return await session.get(Balance, user_id)


async def load_or_create_balance(session: AsyncSession, user_id: int) -> Balance:
    """Same as load_balance, creating an empty balance when there is none."""
    balance = await session.get(Balance, user_id)
    if balance is None:
        balance = Balance(user_id=user_id, stars=Decimal(0))
        session.add(balance)
    return balance


def iam_balance(user_id: int) -> Decimal:
    """
    Баланс IAM из реестра.

    Звёзды живут в SQLite, IAM — в IAMCoinService. Разделение осознанное:
    реестр IAM позже переезжает в ончейн, звёзды остаются платформенными.
    """
    return iam_coin.get_balance(wallet_for(user_id))


@app.get("/api/v1/users/{user_id}/balance/", response_model=BalanceResponse)
async def get_user_balance(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    balance = await load_balance(session, user_id)
    return BalanceResponse(
        stars=str(balance.stars) if balance else "0",
        ia_coins=str(iam_balance(user_id)),
    )


@app.post("/api/v1/users/{user_id}/balance/", response_model=BalanceResponse)
async def update_user_balance(
    user_id: int,
    stars: Optional[float] = None,
    ia_coins: Optional[float] = None,
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    balance = await load_or_create_balance(session, user_id)

    if stars is not None:
        balance.stars = Decimal(str(stars))

    if ia_coins is not None:
        # IAM не лежит в БД: чтобы выставить нужную сумму, доводим её в
        # реестре эмиссией или сжиганием — так эмиссия остаётся честной.
        target = Decimal(str(ia_coins))
        wallet = wallet_for(user_id)
        current = iam_coin.get_balance(wallet)
        try:
            if target > current:
                iam_coin.mint(wallet, target - current, reason="admin_adjust")
            elif target < current:
                iam_coin.burn(wallet, current - target, reason="admin_adjust")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    await session.commit()
    return BalanceResponse(
        stars=str(balance.stars),
        ia_coins=str(iam_balance(user_id)),
    )


# ═══════════════════════════════════════════
# Exchange
# ═══════════════════════════════════════════

@app.get("/api/v1/exchange/rates/", response_model=ExchangeRatesResponse)
async def get_exchange_rates():
    return ExchangeRatesResponse()


@app.post("/api/v1/exchange/")
async def process_exchange(req: ExchangeRequest, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    balance = await load_or_create_balance(session, req.user_id)

    from_amount = Decimal(str(req.from_amount))
    if from_amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")

    # Rate and converted amount come from the server, not from the request.
    # Звёзды меняются в SQLite, IAM — эмиссией и сжиганием в реестре, так что
    # обмен туда-обратно не печатает монеты из воздуха.
    if req.from_currency == "stars":
        rate = RATE_STARS_TO_IA
        if balance.stars < from_amount:
            raise HTTPException(status_code=400, detail="Недостаточно Stars")
        try:
            result = iam_coin.exchange_stars_to_iam(req.user_id, from_amount, rate)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        to_amount = Decimal(result["to_amount"])
        balance.stars -= from_amount
    elif req.from_currency == "ia_coins":
        rate = RATE_IA_TO_STARS
        if iam_balance(req.user_id) < from_amount:
            raise HTTPException(status_code=400, detail="Недостаточно IA-Coins")
        try:
            result = iam_coin.exchange_iam_to_stars(req.user_id, from_amount, rate)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        to_amount = Decimal(result["to_amount"])
        balance.stars += to_amount
    else:
        raise HTTPException(status_code=400, detail="Неизвестная валюта")

    tx = Transaction(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        type="exchange",
        from_currency=req.from_currency,
        to_currency=req.to_currency,
        from_amount=from_amount,
        to_amount=to_amount,
        rate=rate,
    )
    session.add(tx)
    await session.commit()

    return {
        "success": True,
        "from_amount": float(from_amount),
        "to_amount": float(to_amount),
        "rate": float(rate),
        "new_balance": {
            "stars": str(balance.stars),
            "ia_coins": str(iam_balance(req.user_id)),
        },
    }


@app.get("/api/v1/exchange/transactions/{user_id}")
async def get_user_transactions(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.created_at.desc()).limit(100)
    )
    txs = result.scalars().all()
    return [
        {
            "id": tx.id,
            "type": tx.type,
            "from_currency": tx.from_currency,
            "to_currency": tx.to_currency,
            "from_amount": str(tx.from_amount),
            "to_amount": str(tx.to_amount),
            "rate": str(tx.rate),
            "tx_hash": tx.tx_hash,
            "timestamp": tx.created_at.isoformat(),
        }
        for tx in txs
    ]


# ═══════════════════════════════════════════
# Skills
# ═══════════════════════════════════════════

@app.get("/api/v1/skills/skills/")
async def get_skills(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Skill).where(Skill.status == "active"))
    skills = result.scalars().all()
    return {"results": [_skill_to_dict(s) for s in skills]}


@app.get("/api/v1/skills/skills/{skill_id}/")
async def get_skill_details(skill_id: str, session: AsyncSession = Depends(get_session)):
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Навык не найден")
    return _skill_to_dict(skill)


@app.get("/api/v1/skills/skills/featured/")
async def get_featured_skills(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Skill).where(Skill.status == "active").order_by(Skill.popularity_score.desc()).limit(10)
    )
    skills = result.scalars().all()
    return [_skill_to_dict(s) for s in skills]


@app.get("/api/v1/skills/categories/")
async def get_skill_categories(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(SkillCategory))
    cats = result.scalars().all()
    return [
        {"id": c.id, "name": c.name, "icon": c.icon, "skills_count": c.skills_count}
        for c in cats
    ]


@app.post("/api/v1/skills/skills/{skill_id}/install/")
async def install_skill(
    skill_id: str,
    req: SkillInstallRequest,
    session: AsyncSession = Depends(get_session),
):
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Навык не найден")

    bot = await session.get(BotPassport, req.bot_passport_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")

    # Check if already installed
    existing = await session.execute(
        select(SkillInstallation).where(
            SkillInstallation.skill_id == skill_id,
            SkillInstallation.bot_id == req.bot_passport_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Навык уже установлен")

    if bot.owner_id != req.user_id:
        raise HTTPException(
            status_code=403, detail="Ставить навыки может только владелец бота"
        )

    # Charge user
    price = skill.price_ia_coins
    if not skill.is_free and price > 0:
        user = await session.get(User, req.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Оплата идёт из кошелька покупателя в реестре: раньше списание шло
        # из SQLite, а автору платили из казны — два несвязанных события.
        try:
            iam_coin.purchase(
                buyer_wallet=wallet_for(req.user_id),
                creator_wallet=wallet_for(skill.creator_id) if skill.creator_id else None,
                amount=Decimal(str(price)),
                reason="skill_install",
                creator_share=Decimal(str(skill.revenue_creator_share)),
                platform_share=Decimal(str(skill.revenue_platform_share)),
                metadata={"skill_id": skill_id, "bot_id": req.bot_passport_id},
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Create installation
    installation = SkillInstallation(
        id=str(uuid.uuid4()),
        skill_id=skill_id,
        bot_id=req.bot_passport_id,
        user_id=bot.owner_id,
        price_paid=price,
        config=json.dumps(req.config),
    )
    session.add(installation)

    # Update skill stats
    # Счётчики могут быть NULL у строк, созданных не через ORM.
    skill.total_installations = (skill.total_installations or 0) + 1

    await session.commit()

    return {
        "id": installation.id,
        "skill_id": skill_id,
        "skill_name": skill.name,
        "bot_passport_id": req.bot_passport_id,
        "bot_passport_name": bot.name,
        "price_paid": float(price),
        "installed_at": installation.installed_at.isoformat(),
    }


def _skill_to_dict(s: Skill) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "display_name": s.display_name,
        "description": s.description,
        "version": s.version,
        "creator_telegram": s.creator_telegram,
        "category": s.category,
        "category_icon": s.category_icon,
        "price_ia_coins": float(s.price_ia_coins),
        "is_free": s.is_free,
        "average_rating": s.average_rating,
        "ratings_count": s.ratings_count,
        "total_installations": s.total_installations,
        "popularity_score": s.popularity_score,
        "execution_type": s.execution_type,
        "tags": json.loads(s.tags) if s.tags else [],
        "requirements": json.loads(s.requirements) if s.requirements else [],
        "config_schema": json.loads(s.config_schema) if s.config_schema else {},
        "pricing_model": s.pricing_model,
        "status": s.status,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ═══════════════════════════════════════════
# Bot Passports
# ═══════════════════════════════════════════

@app.get("/api/v1/bot-core/bot-passports/")
async def get_bot_passports(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BotPassport))
    bots = result.scalars().all()
    return [_bot_to_dict(b) for b in bots]


@app.get("/api/v1/bot-core/bot-passports/{bot_id}/")
async def get_bot_passport(bot_id: str, session: AsyncSession = Depends(get_session)):
    bot = await session.get(BotPassport, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")
    return _bot_to_dict(bot)


@app.post("/api/v1/bot-core/bot-passports/")
async def create_bot_passport(req: BotPassportCreate, session: AsyncSession = Depends(get_session)):
    bot = BotPassport(
        id=str(uuid.uuid4()),
        owner_id=req.owner_id,
        owner_telegram=req.owner_telegram,
        name=req.name,
        personality=req.personality,
    )
    session.add(bot)
    await session.commit()
    return _bot_to_dict(bot)


@app.get("/api/v1/users/{user_id}/bots/")
async def get_user_bots(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(BotPassport).where(BotPassport.owner_id == user_id)
    )
    bots = result.scalars().all()
    return [_bot_to_dict(b) for b in bots]


@app.get("/api/v1/marketplace/bots/")
async def get_marketplace_bots(session: AsyncSession = Depends(get_session)):
    """
    Bots currently for sale.

    Filters on "listed", not "active": listing sets the status to "listed", so
    the old filter hid every bot actually on sale and offered every working bot
    on the platform instead.
    """
    result = await session.execute(
        select(BotPassport).where(BotPassport.status == "listed")
    )
    bots = result.scalars().all()
    return [
        {
            "id": b.id,
            "name": b.name,
            # `creator` and `price` are what the catalogue screen renders.
            # Without them it died with KeyError on the first listed bot.
            "creator": b.owner_telegram or "—",
            "price": float(b.listing_price_ia_coins or 0),
            "description": b.listing_description or "",
            "owner": b.owner_telegram,
            "level": b.level,
            "personality": b.personality,
            "nft_address": b.nft_address,
        }
        for b in bots
    ]


def _bot_to_dict(b: BotPassport) -> dict:
    return {
        "id": b.id,
        "owner_id": b.owner_id,
        "owner_telegram": b.owner_telegram,
        "name": b.name,
        "personality": b.personality,
        "level": b.level,
        "xp": b.xp,
        "status": b.status,
        "nft_address": b.nft_address,
        "container_id": b.container_id,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


# ═══════════════════════════════════════════
# TON
# ═══════════════════════════════════════════

@app.get("/api/v1/ton/wallet/{user_id}")
async def get_user_ton_wallet(user_id: int, session: AsyncSession = Depends(get_session)):
    wallet = await session.get(TonWallet, user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return {
        "user_id": user_id,
        "ton_address": wallet.address,
    }


@app.post("/api/v1/ton/wallet/{user_id}")
async def create_user_ton_wallet(user_id: int, session: AsyncSession = Depends(get_session)):
    from ton_client import TonWalletManager

    existing = await session.get(TonWallet, user_id)
    if existing:
        raise HTTPException(status_code=400, detail="Wallet already exists")

    try:
        wallet = await TonWalletManager.generate_wallet()
        encrypted = encrypt_secret(wallet.private_key)
    except EncryptionUnavailable as e:
        # Better to refuse than to write a private key in the clear into a
        # column that claims to be encrypted.
        raise HTTPException(status_code=503, detail=str(e))

    db_wallet = TonWallet(
        user_id=user_id,
        address=wallet.address,
        # Both keys are bytes; the columns are text. Store the public key as
        # hex so the reader's bytes.fromhex() actually round-trips.
        public_key=wallet.public_key.hex(),
        encrypted_private_key=encrypted,
    )
    session.add(db_wallet)
    await session.commit()

    return {
        "user_id": user_id,
        "ton_address": wallet.address,
        # The key itself is deliberately not returned in this response; telling
        # the user to save something they were never shown was meaningless.
        "message": "Кошелёк создан. Приватный ключ хранится зашифрованным.",
    }


@app.get("/api/v1/ton/balance/{address}")
async def get_ton_balance(address: str):
    from ton_client import TonClient

    client = TonClient()
    balance = await client.get_address_balance(address)
    return {
        "address": address,
        "balance": str(balance / 1e9),
        "balance_nano": str(balance),
    }


@app.post("/api/v1/ton/transfer/")
async def ton_transfer(
    from_user_id: int,
    to_address: str,
    amount: float,
    token_type: str = "iam_coin",
    session: AsyncSession = Depends(get_session),
):
    from ton_client import TonJettonClient, TonWalletData

    wallet = await session.get(TonWallet, from_user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Sender wallet not found")

    if token_type == "iam_coin":
        jetton = TonJettonClient()
        try:
            private_key = decrypt_secret(wallet.encrypted_private_key)
        except EncryptionUnavailable as e:
            raise HTTPException(status_code=503, detail=str(e))

        wallet_data = TonWalletData(
            address=wallet.address,
            public_key=bytes.fromhex(wallet.public_key) if wallet.public_key else b'',
            private_key=private_key,
        )
        result = await jetton.transfer(wallet_data, to_address, amount)
    else:
        raise HTTPException(status_code=400, detail="Only IAM-coin transfers supported")

    if result.success:
        return {
            "success": True,
            "tx_hash": result.tx_hash,
            "from": wallet.address,
            "to": to_address,
            "amount": amount,
            "token_type": token_type,
        }
    return {"success": False, "error": result.error or "Transfer failed"}


@app.post("/api/v1/ton/nft/mint/")
async def mint_bot_passport(
    owner_id: int,
    bot_id: str,
    bot_name: str,
    metadata: dict,
    session: AsyncSession = Depends(get_session),
):
    from ton_client import TonNFTClient, TonWalletManager

    wallet = await session.get(TonWallet, owner_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Owner wallet not found")

    nft_client = TonNFTClient()
    # TODO: get admin wallet for minting
    admin_wallet = await TonWalletManager.generate_wallet()  # placeholder
    token_id = await nft_client.mint_passport(
        admin_wallet, wallet.address, bot_name, bot_id, metadata
    )

    bot = await session.get(BotPassport, bot_id)
    if bot:
        bot.nft_address = token_id
        await session.commit()

    return {
        "success": True,
        "token_id": token_id,
        "bot_id": bot_id,
        "owner_id": owner_id,
    }


@app.get("/api/v1/ton/nft/{token_id}")
async def get_nft_passport(token_id: str):
    from ton_client import TonNFTClient

    nft_client = TonNFTClient()
    data = await nft_client.get_nft_data(token_id)
    return data or {"error": "NFT not found"}


@app.post("/api/v1/ton/nft/transfer/")
async def transfer_nft_passport(
    from_user_id: int,
    to_address: str,
    token_id: str,
    session: AsyncSession = Depends(get_session),
):
    from ton_client import TonNFTClient

    wallet = await session.get(TonWallet, from_user_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Sender wallet not found")

    nft_client = TonNFTClient()
    result = await nft_client.transfer_passport(wallet.address, to_address, token_id)

    return {
        "success": result.success,
        "tx_hash": result.tx_hash,
        "token_id": token_id,
    }


# ═══════════════════════════════════════════
# Feedback: Bug Reports
# ═══════════════════════════════════════════

@app.post("/api/v1/feedback/bug/")
async def create_bug_report(req: BugReportCreate, session: AsyncSession = Depends(get_session)):
    report = BugReport(
        id=str(uuid.uuid4()),
        user_id=req.user_id,
        bot_id=req.bot_id,
        type=req.type,
        title=req.title,
        description=req.description,
        logs=req.logs,
    )
    session.add(report)
    await session.commit()
    return {
        "id": report.id,
        "status": "open",
        # Уведомление отправляет Скрепка, и только если настроен чат отладки.
        # Раньше здесь безусловно обещали, что разработчики узнают, — при том
        # что уведомлений в платформе не было вообще.
        "message": "Отчёт принят. Мы посмотрим его в ближайшее время.",
    }


@app.get("/api/v1/feedback/bugs/")
async def list_bug_reports(
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    query = select(BugReport).order_by(BugReport.created_at.desc())
    if status:
        query = query.where(BugReport.status == status)
    if user_id:
        query = query.where(BugReport.user_id == user_id)

    result = await session.execute(query.limit(100))
    reports = result.scalars().all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "bot_id": r.bot_id,
            "type": r.type,
            "title": r.title,
            "status": r.status,
            "priority": r.priority,
            "ai_analysis": r.ai_analysis,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in reports
    ]


@app.patch("/api/v1/bot-core/bot-passports/{bot_id}/")
async def update_bot_passport(
    bot_id: str,
    container_id: Optional[str] = None,
    nft_address: Optional[str] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    bot = await session.get(BotPassport, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")
    if container_id:
        bot.container_id = container_id
    if nft_address:
        bot.nft_address = nft_address
    if status:
        bot.status = status
    await session.commit()
    return _bot_to_dict(bot)


@app.get("/api/v1/bot-core/bot-passports/{bot_id}/container/")
async def get_bot_container_id(bot_id: str, session: AsyncSession = Depends(get_session)):
    """Return the Docker container ID for a bot (helpful for logs / debugging)."""
    bot = await session.get(BotPassport, bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Бот не найден")
    return {
        "bot_id": bot.id,
        "container_id": bot.container_id,
        "nft_address": bot.nft_address,
    }


@app.patch("/api/v1/feedback/bugs/{bug_id}/")
async def update_bug_report(
    bug_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    ai_analysis: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    report = await session.get(BugReport, bug_id)
    if not report:
        raise HTTPException(status_code=404, detail="Bug report not found")

    if status:
        report.status = status
        if status == "resolved":
            report.resolved_at = datetime.utcnow()
    if priority:
        report.priority = priority
    if assigned_to:
        report.assigned_to = assigned_to
    if ai_analysis:
        report.ai_analysis = ai_analysis

    await session.commit()
    return {"id": report.id, "status": report.status}


# ═══════════════════════════════════════════
# Feedback: Donations
# ═══════════════════════════════════════════

@app.post("/api/v1/feedback/donate/")
async def create_donation(req: DonationCreate, session: AsyncSession = Depends(get_session)):
    sender = await session.get(User, req.from_user_id)
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")

    amount = Decimal(str(req.amount_ia_coins))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Сумма должна быть положительной")
    if req.to_user_id == req.from_user_id:
        raise HTTPException(status_code=400, detail="Нельзя задонатить самому себе")

    # A donation without a receiver would debit the sender and credit nobody,
    # destroying the coins. Require someone to receive it.
    if not req.to_user_id:
        raise HTTPException(status_code=400, detail="Не указан получатель доната")

    receiver = await session.get(User, req.to_user_id)
    if not receiver:
        raise HTTPException(status_code=404, detail="Получатель не найден")

    # Донат — обычный перевод в реестре, без комиссии: платформа не берёт
    # долю с благодарности разработчику.
    try:
        iam_coin.transfer(
            wallet_for(req.from_user_id),
            wallet_for(req.to_user_id),
            amount,
            reason="donation",
            fee_percent=Decimal("0"),
            metadata={"bug_report_id": req.bug_report_id},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    donation = Donation(
        id=str(uuid.uuid4()),
        from_user_id=req.from_user_id,
        to_user_id=req.to_user_id,
        amount_ia_coins=amount,
        message=req.message,
        bug_report_id=req.bug_report_id,
    )
    session.add(donation)
    await session.commit()

    return {
        "id": donation.id,
        "amount": float(amount),
        "status": "completed",
    }


@app.get("/api/v1/feedback/donations/sent/{user_id}")
async def get_sent_donations(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Donation).where(Donation.from_user_id == user_id).order_by(Donation.created_at.desc()).limit(50)
    )
    donations = result.scalars().all()
    return [
        {
            "id": d.id,
            "to_user_id": d.to_user_id,
            "amount_ia_coins": float(d.amount_ia_coins),
            "message": d.message,
            "bug_report_id": d.bug_report_id,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in donations
    ]


@app.get("/api/v1/feedback/donations/received/{user_id}")
async def get_received_donations(user_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Donation).where(Donation.to_user_id == user_id).order_by(Donation.created_at.desc()).limit(50)
    )
    donations = result.scalars().all()
    return [
        {
            "id": d.id,
            "from_user_id": d.from_user_id,
            "amount_ia_coins": float(d.amount_ia_coins),
            "message": d.message,
            "bug_report_id": d.bug_report_id,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in donations
    ]


# ═══════════════════════════════════════════
# Error Logs (from bot instances)
# ═══════════════════════════════════════════

@app.post("/api/v1/feedback/error-logs/")
async def submit_error_log(req: ErrorLogCreate, session: AsyncSession = Depends(get_session)):
    log = ErrorLog(
        bot_id=req.bot_id,
        user_id=req.user_id,
        error_type=req.error_type,
        message=req.message,
        traceback=req.traceback,
        context=json.dumps(req.context) if req.context else None,
    )
    session.add(log)
    await session.commit()
    return {"id": log.id, "status": "logged"}


@app.get("/api/v1/feedback/error-logs/")
async def get_error_logs(
    bot_id: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    session: AsyncSession = Depends(get_session),
):
    query = select(ErrorLog).order_by(ErrorLog.created_at.desc()).limit(limit)
    if bot_id:
        query = query.where(ErrorLog.bot_id == bot_id)

    result = await session.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "bot_id": log.bot_id,
            "user_id": log.user_id,
            "error_type": log.error_type,
            "message": log.message,
            "traceback": log.traceback,
            "context": json.loads(log.context) if log.context else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ═══════════════════════════════════════════
# Skrepka endpoints
# ═══════════════════════════════════════════

@app.get("/api/v1/skrepka/health/")
async def skrepka_health():
    """Health check for Скрепка integration."""
    return {"status": "ok", "agent": "skrepka"}


@app.post("/api/v1/skrepka/bug-analysis/")
async def skrepka_submit_analysis(
    bug_id: str,
    analysis: str,
    session: AsyncSession = Depends(get_session),
):
    """Скрепка submits AI analysis of a bug report."""
    report = await session.get(BugReport, bug_id)
    if not report:
        raise HTTPException(status_code=404, detail="Bug report not found")

    report.ai_analysis = analysis
    report.status = "triaged"
    await session.commit()

    return {"id": bug_id, "status": "triaged"}


# ═══════════════════════════════════════════
# Marketplace: Skills Publishing & Buying
# ═══════════════════════════════════════════

class SkillPublishRequest(BaseModel):
    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    creator_telegram: str
    category: str
    category_icon: str = ""
    price_ia_coins: float = 0
    is_free: bool = True
    pricing_model: str = "one_time"
    tags: list[str] = []
    requirements: list[str] = []
    config_schema: dict = {}
    execution_type: str = "api_call"


class SkillReviewRequest(BaseModel):
    user_id: int
    skill_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class BotListingRequest(BaseModel):
    bot_id: str
    # Who is listing. Without it the API cannot tell an owner from anyone else
    # who happens to know the bot id.
    seller_id: int
    price_ia_coins: float
    description: str = ""


class BotBuyRequest(BaseModel):
    buyer_id: int
    bot_id: str


class BotUnlistRequest(BaseModel):
    bot_id: str
    seller_id: int


@app.post("/api/v1/marketplace/skills/publish/")
async def publish_skill(req: SkillPublishRequest, session: AsyncSession = Depends(get_session)):
    """Publish a new skill to the marketplace."""
    skill = Skill(
        id=str(uuid.uuid4()),
        name=req.name,
        display_name=req.display_name,
        description=req.description,
        version=req.version,
        creator_telegram=req.creator_telegram,
        category=req.category,
        category_icon=req.category_icon,
        price_ia_coins=Decimal(str(req.price_ia_coins)),
        is_free=req.is_free,
        pricing_model=req.pricing_model,
        tags=json.dumps(req.tags),
        requirements=json.dumps(req.requirements),
        config_schema=json.dumps(req.config_schema),
        execution_type=req.execution_type,
    )
    session.add(skill)
    await session.commit()

    return {
        "id": skill.id,
        "name": skill.name,
        "status": "published",
        "message": "Skill published to marketplace!",
    }


@app.post("/api/v1/marketplace/skills/{skill_id}/review/")
async def review_skill(req: SkillReviewRequest, session: AsyncSession = Depends(get_session)):
    """Submit a review for a skill."""
    skill = await session.get(Skill, req.skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Update rating (simple average)
    ratings_count = skill.ratings_count or 0
    total_rating = (skill.average_rating or 0) * ratings_count + req.rating
    skill.ratings_count = ratings_count + 1
    skill.average_rating = total_rating / skill.ratings_count

    await session.commit()

    return {
        "skill_id": skill.id,
        "new_average": round(skill.average_rating, 2),
        "total_reviews": skill.ratings_count,
    }


@app.get("/api/v1/marketplace/skills/search/")
async def search_skills(
    q: str = "",
    category: str = None,
    min_price: float = None,
    max_price: float = None,
    sort_by: str = "popularity",
    session: AsyncSession = Depends(get_session),
):
    """Search and filter skills."""
    query = select(Skill).where(Skill.status == "active")

    if q:
        query = query.where(
            Skill.name.contains(q) | Skill.display_name.contains(q) | Skill.description.contains(q)
        )
    if category:
        query = query.where(Skill.category == category)
    if min_price is not None:
        query = query.where(Skill.price_ia_coins >= min_price)
    if max_price is not None:
        query = query.where(Skill.price_ia_coins <= max_price)

    if sort_by == "popularity":
        query = query.order_by(Skill.popularity_score.desc())
    elif sort_by == "rating":
        query = query.order_by(Skill.average_rating.desc())
    elif sort_by == "price_low":
        query = query.order_by(Skill.price_ia_coins.asc())
    elif sort_by == "price_high":
        query = query.order_by(Skill.price_ia_coins.desc())
    elif sort_by == "newest":
        query = query.order_by(Skill.created_at.desc())

    result = await session.execute(query.limit(50))
    skills = result.scalars().all()
    return {"results": [_skill_to_dict(s) for s in skills], "total": len(skills)}


# ═══════════════════════════════════════════
# Marketplace: Bot Trading
# ═══════════════════════════════════════════

@app.post("/api/v1/marketplace/bots/{bot_id}/list/")
async def list_bot_for_sale(req: BotListingRequest, session: AsyncSession = Depends(get_session)):
    """List a bot for sale on the marketplace."""
    bot = await session.get(BotPassport, req.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if bot.owner_id != req.seller_id:
        raise HTTPException(status_code=403, detail="Только владелец может выставить бота")

    price = Decimal(str(req.price_ia_coins))
    if price <= 0:
        raise HTTPException(status_code=400, detail="Цена должна быть положительной")

    bot.status = "listed"
    bot.listing_price_ia_coins = price
    bot.listing_description = req.description
    await session.commit()

    return {
        "bot_id": bot.id,
        "price_ia_coins": float(price),
        "status": "listed",
    }


@app.post("/api/v1/marketplace/bots/{bot_id}/unlist/")
async def unlist_bot(req: BotUnlistRequest, session: AsyncSession = Depends(get_session)):
    """Withdraw a bot from sale."""
    bot = await session.get(BotPassport, req.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if bot.owner_id != req.seller_id:
        raise HTTPException(status_code=403, detail="Только владелец может снять бота с продажи")

    bot.status = "active"
    bot.listing_price_ia_coins = None
    await session.commit()
    return {"bot_id": bot.id, "status": "active"}


@app.post("/api/v1/marketplace/bots/{bot_id}/buy/")
async def buy_bot(req: BotBuyRequest, session: AsyncSession = Depends(get_session)):
    """Buy a bot from the marketplace."""
    bot = await session.get(BotPassport, req.bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if bot.status != "listed":
        raise HTTPException(status_code=400, detail="Bot is not for sale")

    if bot.owner_id == req.buyer_id:
        raise HTTPException(status_code=400, detail="Нельзя купить собственного бота")

    buyer = await session.get(User, req.buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")

    # The price the seller actually asked for. A bot cannot reach "listed"
    # without one, but guard anyway rather than silently charging a default.
    if bot.listing_price_ia_coins is None:
        raise HTTPException(status_code=400, detail="У лота не указана цена")
    price = Decimal(str(bot.listing_price_ia_coins))

    # Оплата в реестре: продавец играет роль «автора», остальное уходит
    # платформе. Общая масса монет при сделке не меняется.
    try:
        tx = iam_coin.purchase(
            buyer_wallet=wallet_for(req.buyer_id),
            creator_wallet=wallet_for(bot.owner_id) if bot.owner_id else None,
            amount=price,
            reason="bot_purchase",
            creator_share=SELLER_SHARE,
            platform_share=Decimal("1") - SELLER_SHARE,
            metadata={"bot_id": bot.id},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    seller_amount = Decimal(tx["creator_amount"])
    platform_amount = Decimal(tx["platform_amount"])

    # Transfer ownership
    bot.owner_id = req.buyer_id
    bot.status = "active"
    bot.listing_price_ia_coins = None

    # Record transaction
    tx = Transaction(
        id=str(uuid.uuid4()),
        user_id=req.buyer_id,
        type="bot_purchase",
        from_currency="ia_coins",
        from_amount=price,
        to_currency="bot_ownership",
        to_amount=1,
    )
    session.add(tx)
    await session.commit()

    return {
        "success": True,
        "bot_id": bot.id,
        "new_owner_id": req.buyer_id,
        "price_paid": float(price),
        "seller_received": float(seller_amount),
        "platform_received": float(platform_amount),
    }


# ═══════════════════════════════════════════
# IAM Coin Info
# ═══════════════════════════════════════════

@app.get("/api/v1/iam-coin/info/")
async def iam_coin_info():
    """IAM-coin contract information."""
    # Константы берём из реестра: раньше здесь стояли decimals=2 и supply
    # 2 млрд, притом что IAMCoinService считает в 9 знаках с потолком 1 млрд.
    return {
        "name": "IA Mother",
        "symbol": "IAM",
        "decimals": IAMCoinService.DECIMALS,
        "max_supply": IAMCoinService.MAX_SUPPLY,
        "total_supply": float(iam_coin.get_total_supply()),
        "circulating_supply": float(iam_coin.get_circulating_supply()),
        "master_address": "EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql",
        "admin_address": "EQDLnFGoR9wegeRwhpd9bjyv_MKGXz8sizwC2OO4CZtjIq-s",
        "jetton_wallet_code_hash": "",
        "description": "Safar pro",
    }


@app.get("/api/v1/iam-coin/balance/{address}")
async def get_iam_coin_balance(address: str):
    """Get IAM-coin balance for any address."""
    from ton_client import TonJettonClient
    jetton = TonJettonClient()
    balance = await jetton.get_balance(address)
    return {
        "address": address,
        "balance": float(balance),
        "symbol": "IAM",
    }


# ═══════════════════════════════════════════
# Run
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
