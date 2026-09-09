"""
Разделение валют: звёзды в SQLite, IAM в JSON-реестре.

Решение по архитектуре: реестр IAM позже уезжает в ончейн-минт, поэтому он
единственный источник правды по монетам, а SQLite отвечает только за звёзды.
Раньше IAM лежал в обоих местах сразу, и покупка списывала монеты в одном
хранилище, а начисляла в другом.

Тесты требуют зависимостей Core API; без них пропускаются.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy", reason="зависимости Core API не установлены")
pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

HEADERS = {"X-Core-API-Token": "test-token"}
BUYER, OUTSIDER, AUTHOR = 1, 2, 3


@pytest.fixture
def api(monkeypatch):
    """Поднять Core API на временной БД и временном реестре."""
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.chdir(tmp)
    monkeypatch.setenv("CORE_API_TOKEN", "test-token")
    monkeypatch.setenv("DATA_DIR", str(tmp / "data" / "core_api"))

    # Модули читают окружение на импорте — перезагружаем под текущие настройки.
    import importlib

    import database
    import iam_coin
    import main

    importlib.reload(database)
    importlib.reload(iam_coin)
    importlib.reload(main)

    with TestClient(main.app) as client:
        db = sqlite3.connect(tmp / "data" / "core_api" / "db.sqlite3")
        for uid in (BUYER, OUTSIDER, AUTHOR):
            db.execute(
                "INSERT INTO users (id, telegram_id, username) VALUES (?,?,?)",
                (uid, 100 + uid, f"u{uid}"),
            )
            db.execute(
                "INSERT INTO balances (user_id, stars) VALUES (?,?)",
                (uid, 10000 if uid == BUYER else 0),
            )
        db.execute(
            """INSERT INTO skills (id,name,display_name,description,creator_id,
               price_ia_coins,is_free,revenue_creator_share,revenue_platform_share,
               status,total_installations)
               VALUES ('sk1','weather','Погода','демо',?,100,0,0.6,0.3,'active',0)""",
            (AUTHOR,),
        )
        db.commit()
        db.close()
        client.ledger_path = tmp / "data" / "core_api" / "iam_coin" / "balances.json"
        yield client


def balance(api, user_id):
    return api.get(f"/api/v1/users/{user_id}/balance/", headers=HEADERS).json()


def ledger(api):
    if not api.ledger_path.exists():
        return {}
    return json.loads(api.ledger_path.read_text())["balances"]


def make_bot(api, owner_id):
    return api.post(
        "/api/v1/bot-core/bot-passports/",
        headers=HEADERS,
        json={"owner_id": owner_id, "owner_telegram": "@u", "name": "Ия"},
    ).json()["id"]


def buy_iam(api, user_id, stars):
    return api.post("/api/v1/exchange/", headers=HEADERS, json={
        "user_id": user_id, "from_currency": "stars",
        "to_currency": "ia_coins", "from_amount": stars,
    })


# ── Разделение хранилищ ──

def test_stars_live_in_sqlite_and_iam_in_the_ledger(api):
    buy_iam(api, BUYER, 10000)

    assert balance(api, BUYER) == {"stars": "0E-9", "ia_coins": "100.000000000"}
    assert ledger(api) == {"user_1": "100.000000000"}

    # В SQLite колонки под IAM больше нет.
    db = sqlite3.connect(api.ledger_path.parent.parent / "db.sqlite3")
    columns = {row[1] for row in db.execute("PRAGMA table_info(balances)")}
    db.close()
    assert "ia_coins" not in columns
    assert "stars" in columns


def test_round_trip_exchange_does_not_print_coins(api):
    buy_iam(api, BUYER, 10000)
    supply_after_mint = api.get("/api/v1/iam-coin/info/", headers=HEADERS).json()["total_supply"]

    api.post("/api/v1/exchange/", headers=HEADERS, json={
        "user_id": BUYER, "from_currency": "ia_coins",
        "to_currency": "stars", "from_amount": 100,
    })

    back = balance(api, BUYER)
    assert back["stars"] == "10000.000000000"   # вернулись ровно к началу
    assert back["ia_coins"] == "0E-9"
    assert supply_after_mint == 100.0
    # Обратный обмен сжигает монеты, а не оставляет их в обороте.
    assert api.get("/api/v1/iam-coin/info/", headers=HEADERS).json()["total_supply"] == 0.0


# ── Покупка навыка ──

def test_only_owner_can_install_a_skill(api):
    """Раньше заказчика не спрашивали и списывали с владельца бота."""
    buy_iam(api, BUYER, 10000)
    bot_id = make_bot(api, BUYER)

    r = api.post("/api/v1/skills/skills/sk1/install/", headers=HEADERS,
                 json={"bot_passport_id": bot_id, "user_id": OUTSIDER})

    assert r.status_code == 403
    assert balance(api, BUYER)["ia_coins"] == "100.000000000"  # ничего не списали


def test_purchase_pays_the_author_and_conserves_supply(api):
    buy_iam(api, BUYER, 10000)
    bot_id = make_bot(api, BUYER)

    r = api.post("/api/v1/skills/skills/sk1/install/", headers=HEADERS,
                 json={"bot_passport_id": bot_id, "user_id": BUYER})
    assert r.status_code == 200

    assert balance(api, BUYER)["ia_coins"] == "0E-9"
    # Заработок автора виден в его балансе: раньше он оседал в реестре,
    # который не отдавал ни один эндпоинт.
    assert balance(api, AUTHOR)["ia_coins"] == "60.000000000"

    wallets = ledger(api)
    assert wallets["platform_treasury"] == "30.000000000"
    assert wallets["telegram_fee_wallet"] == "10.000000000"
    assert sum(float(v) for v in wallets.values()) == 100.0


def test_purchase_without_funds_is_refused(api):
    bot_id = make_bot(api, BUYER)   # монет не покупали

    r = api.post("/api/v1/skills/skills/sk1/install/", headers=HEADERS,
                 json={"bot_passport_id": bot_id, "user_id": BUYER})

    assert r.status_code == 400
    assert ledger(api) == {}


# ── Продажа бота ──

def test_bot_sale_moves_iam_through_the_ledger(api):
    buy_iam(api, BUYER, 10000)
    bot_id = make_bot(api, AUTHOR)
    api.post(f"/api/v1/marketplace/bots/{bot_id}/list/", headers=HEADERS,
             json={"bot_id": bot_id, "seller_id": AUTHOR, "price_ia_coins": 100})

    r = api.post(f"/api/v1/marketplace/bots/{bot_id}/buy/", headers=HEADERS,
                 json={"buyer_id": BUYER, "bot_id": bot_id})

    assert r.status_code == 200
    assert r.json()["seller_received"] == 60.0
    assert balance(api, AUTHOR)["ia_coins"] == "60.000000000"
    assert sum(float(v) for v in ledger(api).values()) == 100.0


# ── Донат ──

def test_donation_is_a_ledger_transfer_without_fee(api):
    buy_iam(api, BUYER, 10000)

    r = api.post("/api/v1/feedback/donate/", headers=HEADERS, json={
        "from_user_id": BUYER, "to_user_id": AUTHOR, "amount_ia_coins": 25,
    })

    assert r.status_code == 200
    assert balance(api, AUTHOR)["ia_coins"] == "25.000000000"
    assert balance(api, BUYER)["ia_coins"] == "75.000000000"
    assert sum(float(v) for v in ledger(api).values()) == 100.0
