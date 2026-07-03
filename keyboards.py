from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from utils.emoji import emoji


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{emoji('star')} Купить звёзды", callback_data="buy_start")],
            [InlineKeyboardButton(text=f"{emoji('support')} Поддержка", url=f"https://t.me/{config.SUPPORT_USERNAME}")],
        ]
    )


def confirm_order() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{emoji('check')} Оплатить", callback_data="order_pay")],
            [InlineKeyboardButton(text=f"{emoji('cross')} Отмена", callback_data="order_cancel")],
        ]
    )


def pay_invoice(pay_url: str, invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить в CryptoBot", url=pay_url)],
            [InlineKeyboardButton(text="🔄 Я оплатил / проверить", callback_data=f"check_invoice:{invoice_id}")],
        ]
    )


# --- Админка ---

PERIODS = {
    "day": "За день",
    "week": "За неделю",
    "month": "За месяц",
    "all": "За всё время",
}


def admin_stats_periods(active: str = "all") -> InlineKeyboardMarkup:
    row = []
    labels = {"day": "День", "week": "Неделя", "month": "Месяц", "all": "За все время"}
    for key, label in labels.items():
        text = f"· {label}" if key == active else label
        row.append(InlineKeyboardButton(text=text, callback_data=f"admin_stats:{key}"))

    return InlineKeyboardMarkup(
        inline_keyboard=[
            row,
            [
                InlineKeyboardButton(text=f"{emoji('broadcast')} Рассылка", callback_data="admin_broadcast"),
                InlineKeyboardButton(text=f"{emoji('markup')} Наценки", callback_data="admin_markup"),
            ],
            [InlineKeyboardButton(text="💬 Сообщение после покупки", callback_data="admin_after_purchase")],
        ]
    )


def admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
    )


def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{emoji('check')} Разослать", callback_data="broadcast_send"),
                InlineKeyboardButton(text=f"{emoji('cross')} Отмена", callback_data="broadcast_cancel"),
            ]
        ]
    )
