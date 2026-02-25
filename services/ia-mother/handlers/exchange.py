"""Exchange (Stars ↔ IA-Coins) handlers."""

from telethon import Button, events


async def handle_exchange(event, bot):
    """Exchange screen: balance and rates."""
    user = await event.get_sender()
    balance = await bot.api.get_user_balance(user.id)
    await event.edit(
        f"💱 **Обменник IA-Mother**\n\n"
        f"**Ваш баланс:**\n"
        f"⭐ {balance['stars']} Stars\n"
        f"🪙 {balance['ia_coins']} IA-Coins\n\n"
        f"**Текущие курсы:**\n"
        f"1 Star = {bot.exchange_rates['stars_to_ia_coin']} IA-Coin\n"
        f"1 IA-Coin = {bot.exchange_rates['ia_coin_to_stars']} Stars\n\n"
        f"Что хотите обменять?",
        buttons=[
            [Button.inline("⭐→🪙 Stars → IA-Coins", b"exchange_stars_to_ia")],
            [Button.inline("🪙→⭐ IA-Coins → Stars", b"exchange_ia_to_stars")],
            [Button.inline("📈 История операций", b"exchange_history")],
            [Button.inline("⬅️ Назад", b"back_main")],
        ],
    )


async def handle_exchange_stars_to_ia(event, bot):
    """Stars → IA-Coins choice."""
    await event.edit(
        "⭐→🪙 **Обмен Stars на IA-Coins**\n\n"
        "Введите количество Stars для обмена:\n"
        "(Минимум: 100 Stars)",
        buttons=[
            [Button.inline("100 ⭐", b"exchange_100_stars")],
            [Button.inline("500 ⭐", b"exchange_500_stars")],
            [Button.inline("1000 ⭐", b"exchange_1000_stars")],
            [Button.inline("✏️ Другая сумма", b"exchange_custom_stars")],
            [Button.inline("⬅️ Назад", b"exchange")],
        ],
    )
