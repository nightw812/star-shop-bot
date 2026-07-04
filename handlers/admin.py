import asyncio
import datetime as dt
import logging
from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import config
import keyboards
import texts
from database import async_session, all_user_tg_ids, get_settings, stats_for_period

logger = logging.getLogger(__name__)
router = Router(name="admin")

router.message.filter(F.from_user.id.in_(config.ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(config.ADMIN_IDS))


class AdminStates(StatesGroup):
    waiting_markup_value = State()
    waiting_broadcast_content = State()
    waiting_broadcast_confirm = State()
    waiting_after_purchase_text = State()


def _since_for_period(period: str) -> dt.datetime | None:
    now = dt.datetime.now(dt.timezone.utc)
    if period == "day":
        return now - dt.timedelta(days=1)
    if period == "week":
        return now - dt.timedelta(weeks=1)
    if period == "month":
        return now - dt.timedelta(days=30)
    return None


async def _render_stats(period: str) -> str:
    since = _since_for_period(period)
    async with async_session() as session:
        stats = await stats_for_period(session, since)
    return texts.admin_stats_block(
        keyboards.PERIODS[period],
        stats["new_users"],
        stats["purchases_count"],
        stats["stars_sum"],
        stats["revenue_usdt"],
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = texts.admin_menu_header() + "\n\n" + await _render_stats("all")
    await message.answer(text, reply_markup=keyboards.admin_stats_periods("all"), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_stats:"))
async def admin_stats(callback: CallbackQuery) -> None:
    period = callback.data.split(":", 1)[1]
    text = texts.admin_menu_header() + "\n\n" + await _render_stats(period)
    await callback.message.edit_text(text, reply_markup=keyboards.admin_stats_periods(period), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = texts.admin_menu_header() + "\n\n" + await _render_stats("all")
    await callback.message.edit_text(text, reply_markup=keyboards.admin_stats_periods("all"), parse_mode="HTML")
    await callback.answer()


# --- Наценки / цена ---


@router.callback_query(F.data == "admin_markup")
async def admin_markup(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        settings = await get_settings(session)
    await state.set_state(AdminStates.waiting_markup_value)
    await callback.message.edit_text(
        texts.markup_menu(float(settings.price_per_star_usdt)),
        reply_markup=keyboards.admin_back(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_markup_value)
async def set_markup(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        value = Decimal(raw)
        if value <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.answer("Нужно положительное число, например 0.016. Попробуй ещё раз.")
        return

    async with async_session() as session:
        settings = await get_settings(session)
        settings.price_per_star_usdt = value
        await session.commit()

    await state.clear()
    await message.answer(f"✅ Новая цена: {value} USDT за звезду.")


# --- Сообщение после покупки ---


@router.callback_query(F.data == "admin_after_purchase")
async def admin_after_purchase(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        settings = await get_settings(session)
    await state.set_state(AdminStates.waiting_after_purchase_text)
    await callback.message.edit_text(
        texts.message_after_purchase_prompt(settings.message_after_purchase),
        reply_markup=keyboards.admin_back(),
    )
    await callback.answer()


@router.message(AdminStates.waiting_after_purchase_text)
async def set_after_purchase_text(message: Message, state: FSMContext) -> None:
    new_text = message.html_text or message.text or ""
    async with async_session() as session:
        settings = await get_settings(session)
        settings.message_after_purchase = new_text
        await session.commit()
    await state.clear()
    await message.answer("✅ Сообщение после покупки обновлено.")


# --- Рассылка ---


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_broadcast_content)
    await callback.message.edit_text(texts.broadcast_prompt(), reply_markup=keyboards.admin_back())
    await callback.answer()


@router.message(AdminStates.waiting_broadcast_content)
async def broadcast_content(message: Message, state: FSMContext) -> None:
    await state.update_data(broadcast_message_id=message.message_id, broadcast_chat_id=message.chat.id)
    await state.set_state(AdminStates.waiting_broadcast_confirm)

    async with async_session() as session:
        recipients = await all_user_tg_ids(session)
    await state.update_data(recipients=recipients)

    await message.answer(texts.broadcast_confirm(len(recipients)), reply_markup=keyboards.broadcast_confirm_kb())


@router.callback_query(AdminStates.waiting_broadcast_confirm, F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Рассылка отменена.")
    await callback.answer()


@router.callback_query(AdminStates.waiting_broadcast_confirm, F.data == "broadcast_send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await state.clear()
    recipients: list[int] = data["recipients"]
    source_chat_id = data["broadcast_chat_id"]
    source_message_id = data["broadcast_message_id"]

    await callback.message.edit_text(f"⏳ Рассылаю {len(recipients)} пользователям…")
    await callback.answer()

    sent, failed = 0, 0
    for tg_id in recipients:
        try:
            await callback.bot.copy_message(chat_id=tg_id, from_chat_id=source_chat_id, message_id=source_message_id)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # анти-флуд лимит Telegram

    await callback.message.answer(texts.broadcast_done(sent, failed), parse_mode="HTML")
