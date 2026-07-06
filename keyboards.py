from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from utils.emoji import emoji_id, plain

BACK = InlineKeyboardButton(text=" Назад", callback_data="nav_back", icon_custom_emoji_id=emoji_id("back"))

AMOUNT_PRESETS = [50, 150, 250, 350, 500, 1000]


def _btn(text: str, emoji_key: str | None = None, **kwargs) -> InlineKeyboardButton:
    """Кнопка с кастомным emoji-иконкой (если задан ID в utils/emoji.py) и обычным
    emoji прямо в тексте как fallback — если владелец бота без Premium, иконка просто
    не покажется, а текстовый emoji останется."""
    icon = emoji_id(emoji_key) if emoji_key else None
    return InlineKeyboardButton(text=text, icon_custom_emoji_id=icon, **kwargs)


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(f"Звёзды", "star", callback_data="stars_menu"),
                _btn(" Premium", "premium", callback_data="premium_menu"),
            ],
            [
                _btn(f" Поддержка", "support", url=f"https://t.me/{config.SUPPORT_USERNAME}"),
                _btn(" Профиль", "profile", callback_data="profile_menu"),
            ],
        ]
    )


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[BACK]])


def type_menu(product: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(f" Себе", "self", callback_data=f"type_self:{product}"),
                _btn(f" Подарить", "gift", callback_data=f"type_gift:{product}"),
            ],
            [BACK],
        ]
    )


def premium_months() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=f"{m} мес.", callback_data=f"premium_months:{m}")
        for m in config.PREMIUM_MONTH_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row, [BACK]])


def only_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[BACK]])


def amount_select() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for i, value in enumerate(AMOUNT_PRESETS, start=1):
        row.append(InlineKeyboardButton(text=f"{value}", callback_data=f"amount_preset:{value}"))
        if i % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="Выбрать количество", callback_data="amount_custom")])
    rows.append([BACK])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_method() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="USDT • 3%", callback_data="pay_usdt")],
            [BACK],
        ]
    )


def markup_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Звёзды", callback_data="markup_stars")],
            [InlineKeyboardButton(text="💎 Premium", callback_data="markup_premium")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
        ]
    )


def premium_markup_months_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{m} мес.", callback_data=f"markup_premium_month:{m}")]
        for m in config.PREMIUM_MONTH_OPTIONS
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_markup")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pay_invoice(pay_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить", url=pay_url)],
            [BACK],
        ]
    )


# --- Админка ---


def admin_menu(maintenance_enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(f"{plain('stats')} Статистика", "stats", callback_data="admin_stats")],
            [
                InlineKeyboardButton(
                    text=f"🛠 Тех.работы: {'ВКЛ ✅' if maintenance_enabled else 'ВЫКЛ ❌'}",
                    callback_data="admin_toggle_maintenance",
                )
            ],
            [
                _btn(f"{plain('broadcast')} Рассылка", "broadcast", callback_data="admin_broadcast"),
                _btn(f"{plain('markup')} Наценки", "markup", callback_data="admin_markup"),
            ],
            [InlineKeyboardButton(text="💬 Сообщение после покупки", callback_data="admin_after_purchase")],
        ]
    )


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _btn(f"{plain('check')} Разослать", "check", callback_data="broadcast_send"),
                _btn(f"{plain('cross')} Отмена", "cross", callback_data="broadcast_cancel"),
            ]
        ]
    )


def admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
    )
