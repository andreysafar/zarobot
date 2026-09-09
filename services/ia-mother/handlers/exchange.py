"""Exchange handlers: IAM-coin ↔ Stars and IAM-coin info."""

from telethon import Button, events
from decimal import Decimal


async def handle_exchange(event, bot):
    """Exchange screen: balance and rates."""
    user = await event.get_sender()
    balance = await bot.api.get_user_balance(user.id)
    rates = await bot.api.get_exchange_rates()

    stars_to_iam = rates["stars_to_ia_coin"] if rates else Decimal("1")
    iam_to_stars = rates["ia_coin_to_stars"] if rates else Decimal("1")

    await event.edit(
        f"💱 **Обменник IA-Mother**\n\n"
        f"**Ваш баланс:**\n"
        f"🪙 {balance['ia_coins']} IA-Coins\n"
        f"⭐ {balance['stars']} Stars\n\n"
        f"**Текущие курсы:**\n"
        f"1 Star = {stars_to_iam} IA-Coin\n"
        f"1 IA-Coin = {iam_to_stars} Stars\n\n"
        f"🪙 **IAM Coin** — токен платформы Zero Bot\n"
        f"Контракт: `EQC3PJDocLYLoyOk_BAmmgzlZ-YEZ9yZcOIebMcfc8EwEjql`\n\n"
        f"Что хотите сделать?",
        buttons=[
            [Button.inline("⭐→🪙 Купить IA-Coins", b"exchange_stars_to_ia")],
            [Button.inline("🪙→⭐ Продать IA-Coins", b"exchange_ia_to_stars")],
            [Button.inline("📈 История операций", b"exchange_history")],
            [Button.inline("⬅️ Назад", b"back_main")],
        ],
    )


# Номиналы кнопок задаём в звёздах: столько пользователь реально тратит.
STAR_PRESETS = (100, 500, 1000)
# Обратно — в IAM; сколько это звёзд, считаем по курсу, а не пишем руками.
IAM_PRESETS = (1, 5, 10)


def _fmt(value) -> str:
    """Убрать хвостовые нули: 1.000000000 → 1."""
    d = Decimal(str(value)).normalize()
    return format(d, "f")


async def handle_exchange_stars_to_ia(event, bot):
    """Экран покупки IA-Coins за звёзды."""
    rates = await bot.api.get_exchange_rates()
    rate = rates["stars_to_ia_coin"] if rates else Decimal("0.01")

    # Подписи считаем от курса. Раньше здесь было зашито «100 ⭐ → 100 IAM»
    # при реальном курсе 0.01 — интерфейс обещал в сто раз больше, чем даёт.
    buttons = [
        [Button.inline(
            f"{amount} ⭐ → {_fmt(Decimal(amount) * rate)} IAM",
            f"exchange_do_stars_{amount}".encode(),
        )]
        for amount in STAR_PRESETS
    ]
    buttons.append([Button.inline("⬅️ Назад", b"exchange")])

    await event.edit(
        "⭐→🪙 **Покупка IA-Coins**\n\n"
        f"Курс: 1 ⭐ = {_fmt(rate)} IAM\n\n"
        "Выберите сумму:",
        buttons=buttons,
    )


async def handle_exchange_ia_to_stars(event, bot):
    """Экран продажи IA-Coins за звёзды."""
    rates = await bot.api.get_exchange_rates()
    rate = rates["ia_coin_to_stars"] if rates else Decimal("100")

    buttons = [
        [Button.inline(
            f"{amount} IAM → {_fmt(Decimal(amount) * rate)} ⭐",
            f"exchange_do_iam_{amount}".encode(),
        )]
        for amount in IAM_PRESETS
    ]
    buttons.append([Button.inline("⬅️ Назад", b"exchange")])

    await event.edit(
        "🪙→⭐ **Продажа IA-Coins**\n\n"
        f"Курс: 1 IAM = {_fmt(rate)} ⭐\n\n"
        "Выберите сумму:",
        buttons=buttons,
    )


async def handle_exchange_execute(event, bot):
    """
    Выполнить обмен по нажатой кнопке.

    Сюда приходят колбэки exchange_do_<валюта>_<сумма>. Раньше кнопки
    номиналов вообще ни к чему не были подключены — нажатие не делало ничего.
    """
    kind = event.pattern_match.group(1).decode()
    amount = Decimal(event.pattern_match.group(2).decode())
    user = await event.get_sender()

    from_currency = "stars" if kind == "stars" else "ia_coins"
    result = await bot.api.process_exchange(user.id, from_currency, amount)

    back = [[Button.inline("⬅️ К обменнику", b"exchange")]]
    if not result.get("success"):
        await event.edit(
            f"❌ Обмен не выполнен.\n\n{result.get('error', 'Попробуйте позже.')}",
            buttons=back,
        )
        return

    got_unit = "IAM" if from_currency == "stars" else "⭐"
    gave_unit = "⭐" if from_currency == "stars" else "IAM"
    balance = result.get("new_balance", {})
    await event.edit(
        f"✅ **Обмен выполнен**\n\n"
        f"Отдано: {_fmt(result['from_amount'])} {gave_unit}\n"
        f"Получено: {_fmt(result['to_amount'])} {got_unit}\n\n"
        f"**Баланс:**\n"
        f"⭐ {_fmt(balance.get('stars', 0))} Stars\n"
        f"🪙 {_fmt(balance.get('ia_coins', 0))} IA-Coins",
        buttons=back,
    )


async def handle_exchange_history(event, bot):
    """Show user's transaction history."""
    user = await event.get_sender()
    try:
        txs = await bot.api._request("GET", f"/api/v1/exchange/transactions/{user.id}")
        if not txs:
            await event.edit(
                "📈 **История операций**\n\n"
                "У вас пока нет операций.",
                buttons=[[Button.inline("⬅️ Назад", b"exchange")]],
            )
            return

        text = "📈 **История операций:**\n\n"
        for tx in txs[:10]:
            emoji = "🟢" if tx.get("type") == "exchange" else "🔵"
            text += (
                f"{emoji} {tx.get('type', 'unknown')}\n"
                f"   {tx.get('from_amount', '?')} {tx.get('from_currency', '?')} "
                f"→ {tx.get('to_amount', '?')} {tx.get('to_currency', '?')}\n"
                f"   📅 {tx.get('timestamp', '?')[:16]}\n\n"
            )
        await event.edit(text, buttons=[[Button.inline("⬅️ Назад", b"exchange")]])
    except Exception:
        await event.edit(
            "📈 **История операций**\n\n"
            "Не удалось загрузить историю. Попробуйте позже.",
            buttons=[[Button.inline("⬅️ Назад", b"exchange")]],
        )
