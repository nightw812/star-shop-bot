import asyncio
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
from database import all_user_tg_ids, async_session, get_premium_prices, get_settings, recent_purchases, set_premium_prices

logger = logging.getLogger(__name__)
router = Router(name="admin")

router.message.filter(F.from_user.id.in_(config.ADMIN_IDS))
router.callback_query.filter(F.from_user.id.in_(config.ADMIN_IDS))


class AdminStates(StatesGroup):
    waiting_markup_stars_value = State()
    waiting_markup_premium_value = State()
    waiting_broadcast_content = State()
    waiting_broadcast_confirm = State()
    waiting_after_purchase_text = State()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        settings = await get_settings(session)
    await message.answer(
        texts.admin_menu_header(),
        reply_markup=keyboards.admin_menu(settings.maintenance_mode),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        settings = await get_settings(session)
    await callback.message.edit_text(
        texts.admin_menu_header(),
        reply_markup=keyboards.admin_menu(settings.maintenance_mode),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery) -> None:
    async with async_session() as session:
        purchases = await recent_purchases(session, limit=20)

    if not purchases:
        text = texts.admin_stats_empty()
    else:
        entries = "\n\n".join(texts.admin_stats_entry(p) for p in purchases)
        text = f"{texts.admin_menu_header()}\n\n" + entries

    await callback.message.edit_text(text, reply_markup=keyboards.admin_back(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_toggle_maintenance")
async def admin_toggle_maintenance(callback: CallbackQuery) -> None:
    async with async_session() as session:
        settings = await get_settings(session)
        settings.maintenance_mode = not settings.maintenance_mode
        await session.commit()
        new_state = settings.maintenance_mode

    await callback.message.edit_text(
        texts.admin_menu_header(),
        reply_markup=keyboards.admin_menu(new_state),
        parse_mode="HTML",
    )
    await callback.answer(texts.maintenance_status(new_state))


# --- Наценки: выбор товара ---


@router.callback_query(F.data == "admin_markup")
async def admin_markup_choice(callback: CallbackQuery) -> None:
    await callback.message.edit_text(texts.markup_choice(), reply_markup=keyboards.markup_choice_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "markup_stars")
async def admin_markup_stars(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        settings = await get_settings(session)
    await state.set_state(AdminStates.waiting_markup_stars_value)
    await callback.message.edit_text(
        texts.markup_menu(settings.price_per_star_rub), reply_markup=keyboards.admin_back(), parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_markup_stars_value)
async def set_markup_stars(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip().replace(",", ".")
    try:
        value = Decimal(raw)
        if value <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.reply("Нужно положительное число, например 1.3. Попробуйте ещё раз.")
        return

    async with async_session() as session:
        settings = await get_settings(session)
        settings.price_per_star_rub = value
        await session.commit()

    await state.clear()
    await message.reply(f"✅ Новая цена: {value} ₽ за звезду.")


@router.callback_query(F.data == "markup_premium")
async def admin_markup_premium(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        texts.premium_markup_choice(), reply_markup=keyboards.premium_markup_months_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("markup_premium_month:"))
async def admin_markup_premium_month(callback: CallbackQuery, state: FSMContext) -> None:
    months = int(callback.data.split(":", 1)[1])
    async with async_session() as session:
        settings = await get_settings(session)
    prices = get_premium_prices(settings)
    await state.set_state(AdminStates.waiting_markup_premium_value)
    await state.update_data(markup_premium_months=months)
    await callback.message.edit_text(
        texts.premium_markup_menu(months, prices.get(months, 0)),
        reply_markup=keyboards.admin_back(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.waiting_markup_premium_value)
async def set_markup_premium(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    months = data["markup_premium_months"]
    raw = (message.text or "").strip().replace(",", ".")
    try:
        value = Decimal(raw)
        if value <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await message.reply("Нужно положительное число, например 1200. Попробуйте ещё раз.")
        return

    async with async_session() as session:
        settings = await get_settings(session)
        prices = get_premium_prices(settings)
        prices[months] = value
        await set_premium_prices(session, settings, prices)

    await state.clear()
    await message.reply(f"✅ Новая цена Premium на {months} мес.: {value} ₽.")


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
    await message.reply("✅ Сообщение после покупки обновлено.")


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

    await message.reply(texts.broadcast_confirm(len(recipients)), reply_markup=keyboards.broadcast_confirm_kb())


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
