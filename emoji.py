"""
Поддержка кастомных эмодзи Telegram Premium.

Кастомный эмодзи в HTML выглядит так:
    <tg-emoji emoji-id="5368324170671202286">⭐</tg-emoji>
где emoji-id — числовой ID конкретного premium-эмодзи, а символ внутри тега —
обычный emoji-фолбэк для тех, у кого нет Telegram Premium (или для ботов без
разрешения показывать custom emoji).

Как узнать emoji-id: перешли нужный кастомный эмодзи любому боту вроде
@like_id_bot / @EmojiIdBot (или можно получить через getCustomEmojiStickers /
разбор entities входящего сообщения с этим эмодзи).

ВАЖНО: сообщения с <tg-emoji> нужно отправлять с parse_mode="HTML".
Если id не задан (None или пустая строка) — используется обычный emoji без тега,
бот не сломается, просто без "премиум" вида.
"""

# Заполни реальными ID своих кастомных эмодзи (или оставь None — будет обычный emoji)
CUSTOM_EMOJI_IDS: dict[str, str | None] = {
    "star": None,       # ⭐
    "admin": None,       # 🛠
    "stats": None,       # 📊
    "money": None,       # 💰
    "broadcast": None,   # 💬
    "markup": None,      # 💲
    "support": None,     # 🆘
    "check": None,       # ✅
    "cross": None,       # ❌
    "hourglass": None,   # ⏳
}

_FALLBACK = {
    "star": "⭐",
    "admin": "🛠",
    "stats": "📊",
    "money": "💰",
    "broadcast": "💬",
    "markup": "💲",
    "support": "🆘",
    "check": "✅",
    "cross": "❌",
    "hourglass": "⏳",
}


def emoji(name: str) -> str:
    """Возвращает HTML-фрагмент с кастомным эмодзи (если задан id) или обычный emoji."""
    fallback = _FALLBACK.get(name, "")
    custom_id = CUSTOM_EMOJI_IDS.get(name)
    if custom_id:
        return f'<tg-emoji emoji-id="{custom_id}">{fallback}</tg-emoji>'
    return fallback
