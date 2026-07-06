import logging
import re
from decimal import Decimal
from typing import Any

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, TelegramObject

import config
import keyboards
import texts
from database import (
    async_session,
    create_purchase,
    get_or_create_user,
    get_premium_prices,
    get_settings,
    get_user_by_tg_id,
    user_profile_stats,
)
from services import cryptopay_service, fragment_service

logger = logging.getLogger(__name__)
router = Router(name="user")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{5,32}$")

# Грубый курс для отображения "≈ $" в профиле (просто ориентир, не влияет на расчёты оплаты)
_RUB_PER_USD = 90


class Flow(StatesGroup):
    waiting_text = State()


class MaintenanceMiddleware(BaseMiddleware):
    """Блокирует обычных пользователей во время технических работ, админов пропускает."""

    async def __call__(self, handler, event: TelegramObject, data: dict[str, Any]):
        user = data.get("event_from_user")
        if user and user.id not in config.ADMIN_IDS:
            async with async_session() as session:
                settings = await get_settings(session)
            if settings.maintenance_mode:
                if isinstance(event, Message):
                    await event.answer(texts.maintenance_message())
                elif isinstance(event, CallbackQuery):
                    await event.answer(texts.maintenance_message(), show_alert=True)
                return None
        return await handler(event, data)


router.message.middleware(MaintenanceMiddleware())
router.callback_query.middleware(MaintenanceMiddleware())


def normalize_username(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        raw = raw.split("https://t.me/", 1)[1]
    return raw.lstrip("@").strip()


async def _delete_previous(event, ctx: dict) -> None:
    if isinstance(event, CallbackQuery):
        try:
            await event.message.delete()
        except Exception:
            pass
    else:
        last_id = ctx.get("last_bot_msg_id")
        if last_id:
            try:
                await event.bot.delete_message(chat_id=event.chat.id, message_id=last_id)
            except Exception:
                pass


async def _send(event, text: str, keyboard=None) -> int:
    """Отправляет новое сообщение. Если событие — текст от пользователя, отвечает
    с цитированием (reply), чтобы было видно, на какое сообщение это ответ."""
    bot = event.bot
    if isinstance(event, CallbackQuery):
        msg = await bot.send_message(chat_id=event.message.chat.id, text=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        msg = await event.reply(text, reply_markup=keyboard, parse_mode="HTML")
    return msg.message_id


async def render(screen: str, event, state: FSMContext) -> None:
    """Рисует нужный экран: удаляет предыдущее сообщение бота и присылает новое."""
    ctx = await state.get_data()
    username = ctx.get("username")
    amount = ctx.get("amount")

    await _delete_previous(event, ctx)

    waiting = False

    if screen == "main":
        text, kb = texts.welcome(), keyboards.main_menu()
    elif screen == "stars_type":
        text, kb = texts.stars_type(), keyboards.type_menu("stars")
    elif screen == "premium_type":
        text, kb = texts.premium_type(), keyboards.type_menu("premium")
    elif screen == "ask_recipient":
        text, kb = texts.ask_recipient_username(), keyboards.only_back()
        waiting = True
    elif screen == "amount_select":
        text, kb = f"Выберите количество звёзд для @{username}:", keyboards.amount_select()
    elif screen == "custom_amount_prompt":
        text, kb = texts.choose_amount(username), keyboards.only_back()
        waiting = True
    elif screen == "premium_months_select":
        text, kb = texts.choose_premium_months(username), keyboards.premium_months()
    elif screen == "price_confirm":
        async with async_session() as session:
            settings = await get_settings(session)
        total_rub = (Decimal(amount) * settings.price_per_star_rub).quantize(Decimal("1"))
        text, kb = texts.price_confirm(amount, total_rub), keyboards.payment_method()
        await state.update_data(base_total_rub=str(total_rub))
    elif screen == "premium_price_confirm":
        async with async_session() as session:
            settings = await get_settings(session)
        prices = get_premium_prices(settings)
        total_rub = prices.get(amount, Decimal("0"))
        text, kb = texts.premium_price_confirm(amount, total_rub), keyboards.payment_method()
        await state.update_data(base_total_rub=str(total_rub))
    elif screen == "profile":
        async with async_session() as session:
            user = await get_user_by_tg_id(session, event.from_user.id)
            stats = await user_profile_stats(session, event.from_user.id)
        joined_at = user.created_at if user else None
        approx_usd = stats["total_stars"] * float(config.DEFAULT_PRICE_PER_STAR_RUB) / _RUB_PER_USD
        text = texts.profile(event.from_user.id, joined_at, stats["total_stars"], approx_usd)
        kb = keyboards.profile_kb()
    else:
        text, kb = texts.welcome(), keyboards.main_menu()
        screen = "main"

    new_id = await _send(event, text, kb)

    await state.set_state(Flow.waiting_text if waiting else None)
    await state.update_data(screen=screen, last_bot_msg_id=new_id)


async def goto(screen: str, event, state: FSMContext, **updates) -> None:
    ctx = await state.get_data()
    stack = ctx.get("nav_stack", [])
    stack.append(ctx.get("screen", "main"))
    await state.update_data(nav_stack=stack, **updates)
    await render(screen, event, state)


async def go_back(event, state: FSMContext) -> None:
    ctx = await state.get_data()
    stack = ctx.get("nav_stack", [])
    target = stack.pop() if stack else "main"
    await state.update_data(nav_stack=stack)
    await render(target, event, state)


async def show_no_username_error(event, state: FSMContext) -> None:
    ctx = await state.get_data()
    await _delete_previous(event, ctx)
    new_id = await _send(event, texts.no_username_error(), keyboards.only_back())
    stack = ctx.get("nav_stack", [])
    stack.append(ctx.get("screen", "main"))
    await state.update_data(last_bot_msg_id=new_id, nav_stack=stack, screen="no_username_error")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.username)

    if config.WELCOME_STICKER_ID:
        try:
            await message.answer_sticker(config.WELCOME_STICKER_ID)
        except Exception:
            logger.warning("Не удалось отправить приветственный стикер — проверь WELCOME_STICKER_ID")

    msg = await message.answer(texts.welcome(), reply_markup=keyboards.main_menu())
    await state.update_data(screen="main", nav_stack=[], last_bot_msg_id=msg.message_id)


@router.callback_query(F.data == "nav_back")
async def nav_back(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await go_back(callback, state)


@router.callback_query(F.data == "stars_menu")
async def stars_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await goto("stars_type", callback, state, product="stars")


@router.callback_query(F.data == "premium_menu")
async def premium_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await goto("premium_type", callback, state, product="premium")


@router.callback_query(F.data == "profile_menu")
async def profile_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await goto("profile", callback, state)


@router.callback_query(F.data.startswith("type_self:"))
async def type_self(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product = callback.data.split(":", 1)[1]
    username = callback.from_user.username
    if not username:
        await show_no_username_error(callback, state)
        return
    next_screen = "amount_select" if product == "stars" else "premium_months_select"
    await goto(next_screen, callback, state, username=username, purchase_type="self", product=product)


@router.callback_query(F.data.startswith("type_gift:"))
async def type_gift(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    product = callback.data.split(":", 1)[1]
    await goto("ask_recipient", callback, state, purchase_type="gift", product=product)


@router.message(Flow.waiting_text)
async def waiting_text_router(message: Message, state: FSMContext) -> None:
    ctx = await state.get_data()
    screen = ctx.get("screen")
    if screen == "ask_recipient":
        await process_recipient_username(message, state)
    elif screen == "custom_amount_prompt":
        await process_custom_amount(message, state)


async def process_recipient_username(message: Message, state: FSMContext) -> None:
    ctx = await state.get_data()
    product = ctx.get("product", "stars")
    username = normalize_username(message.text or "")
    if not USERNAME_RE.match(username):
        await message.reply("Юзернейм некорректен (5-32 символа, латиница/цифры/_). Попробуйте ещё раз.")
        return

    exists = False
    try:
        exists = await fragment_service.check_username_exists(username)
    except Exception:
        logger.exception("Ошибка проверки юзернейма %s", username)

    if not exists:
        msg = await message.reply(texts.username_not_found(username), reply_markup=keyboards.only_back())
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    next_screen = "amount_select" if product == "stars" else "premium_months_select"
    await goto(next_screen, message, state, username=username)


async def process_custom_amount(message: Message, state: FSMContext) -> None:
    ctx = await state.get_data()
    username = ctx.get("username")
    raw = (message.text or "").strip().replace(" ", "")

    if not raw.isdigit():
        msg = await message.reply(texts.not_integer_error(), reply_markup=keyboards.only_back())
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    amount = int(raw)
    if not (config.MIN_STARS <= amount <= config.MAX_STARS):
        msg = await message.reply(texts.amount_out_of_range_error(username), reply_markup=keyboards.only_back())
        await state.update_data(last_bot_msg_id=msg.message_id)
        return

    await goto("price_confirm", message, state, amount=amount)


@router.callback_query(F.data.startswith("amount_preset:"))
async def amount_preset(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    amount = int(callback.data.split(":", 1)[1])
    await goto("price_confirm", callback, state, amount=amount)


@router.callback_query(F.data == "amount_custom")
async def amount_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await goto("custom_amount_prompt", callback, state)


@router.callback_query(F.data.startswith("premium_months:"))
async def premium_months(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    months = int(callback.data.split(":", 1)[1])
    await goto("premium_price_confirm", callback, state, amount=months)


@router.callback_query(F.data == "pay_usdt")
async def pay_usdt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    ctx = await state.get_data()
    username = ctx["username"]
    amount = ctx["amount"]  # звёзды или месяцы Premium, в зависимости от product
    product = ctx.get("product", "stars")
    base_total_rub = Decimal(ctx["base_total_rub"])
    total_with_fee = cryptopay_service.apply_cryptobot_fee(base_total_rub)

    description = (
        f"{amount} Telegram Stars для @{username}" if product == "stars" else f"Premium {amount} мес. для @{username}"
    )
    invoice = await cryptopay_service.create_invoice(
        amount_rub=total_with_fee,
        description=description,
        payload=f"{callback.from_user.id}:{username}:{amount}:{product}",
    )

    async with async_session() as session:
        await create_purchase(
            session,
            user_tg_id=callback.from_user.id,
            buyer_username=callback.from_user.username,
            purchase_type=ctx.get("purchase_type", "gift"),
            product=product,
            recipient_username=username,
            stars_amount=amount,
            price_rub=total_with_fee,
            invoice_id=invoice.invoice_id,
        )

    invoice_text = (
        texts.invoice_message(username, amount, int(total_with_fee))
        if product == "stars"
        else texts.premium_invoice_message(username, amount, int(total_with_fee))
    )

    await _delete_previous(callback, ctx)
    new_id = await _send(callback, invoice_text, keyboards.pay_invoice(invoice.bot_invoice_url))
    stack = ctx.get("nav_stack", [])
    stack.append(ctx.get("screen", "main"))
    await state.update_data(screen="invoice", last_bot_msg_id=new_id, nav_stack=stack)
