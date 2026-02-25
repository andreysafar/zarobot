"""Platform stats handler."""

from telethon import Button, events


async def handle_stats(event, bot):
    """Platform statistics screen."""
    stats = await bot.api.get_platform_stats()
    await event.edit(
        f"📊 **Статистика Zero Bot**\n\n"
        f"🤖 **Боты:** {stats['total_bots']}\n"
        f"👥 **Пользователи:** {stats['total_users']}\n"
        f"🧠 **Навыки:** {stats['total_skills']}\n"
        f"👑 **Личности:** {stats['total_personalities']}\n\n"
        f"💰 **Экономика:**\n"
        f"🪙 IA-Coins в обороте: {stats['ia_coins_supply']}\n"
        f"💎 NFT Паспортов: {stats['nft_passports']}\n"
        f"💸 Объем торгов: {stats['trading_volume']} IA-Coins\n\n"
        f"🔥 **За последние 24 часа:**\n"
        f"📈 Новых ботов: {stats['new_bots_24h']}\n"
        f"💬 Сообщений: {stats['messages_24h']}\n"
        f"💰 Транзакций: {stats['transactions_24h']}",
        buttons=[
            [Button.inline("📈 Подробная аналитика", b"detailed_stats")],
            [Button.inline("⬅️ Назад", b"back_main")],
        ],
    )
