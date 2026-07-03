import asyncio
import logging
import re
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from pyfragment import FragmentError

import config
import keyboards
import texts
from database import async_session, create_purchase, get_or_create_user, get_purchase_by_invoice, get_settings, mark_purchase
from services import cryptopay_service, fragment_service

logger = logging.getLogger(__name__)
router = Router(name="user")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{5,32}$")


class BuyStars(StatesGroup):
    waiting_username = State()
    waiting_amount = State()


def normalize_username(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        raw = raw.split("https://t.me/", 1)[1]
    return raw.lstrip("@").strip()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with async_session() as session:
        await get_or_create_user(session, message.from_user.id, message.from_user.username)
    await message.answer(texts.welcome(), reply_markup=keyboards.main_menu(), parse_mode="HTML")


@router.callback_query(F.data == "buy_start")
async def buy_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BuyStars.waiting_username)
    await callback.message.edit_text(texts.ask_username())
    await callback.answer()


@router.message(BuyStars.waiting_username)
async def process_username(message: Message, state: FSMContext) -> None:
    username = normalize_username(message.text or "")
    if not USERNAME_RE.match(username):
        await message.answer("Юзернейм некорректен (5-32 символа, латиница/цифры/_). Попробуй ещё раз.")
        return

    async with async_session() as session:
        settings = await get_settings(session)
        price = float(settings.price_per_star_usdt)

    await state.update_data(username=username, price_per_star=price)
    await state.set_state(BuyStars.waiting_amount)
    await message.answer(texts.ask_amount(username, price), parse_mode="HTML")


@router.message(BuyStars.waiting_amount)
async def process_amount(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().replace(" ", "")
    if not text.isdigit():
        await message.answer("Нужно целое число. Попробуй ещё раз.")
        return

    amount = int(text)
    if not (config.MIN_STARS <= amount <= config.MAX_STARS):
        await message.answer(f"Количество должно быть от {config.MIN_STARS} до {config.MAX_STARS}.")
        return

    data = await state.update_data(amount=amount)
    total = round(amount * data["price_per_star"], 4)
    await state.update_data(total_price=total)

    await message.answer(
        texts.order_summary(data["username"], amount, total),
        reply_markup=keyboards.confirm_order(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "order_cancel")
async def order_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Заказ отменён.")
    await callback.answer()


@router.callback_query(F.data == "order_pay")
async def order_pay(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    username = data["username"]
    amount = data["amount"]
    total_price = Decimal(str(data["total_price"]))
    await state.clear()

    invoice = await cryptopay_service.create_invoice(
        amount_usdt=total_price,
        description=f"{amount} Telegram Stars для @{username}",
        payload=f"{callback.from_user.id}:{username}:{amount}",
    )

    async with async_session() as session:
        await create_purchase(
            session,
            user_tg_id=callback.from_user.id,
            recipient_username=username,
            stars_amount=amount,
            price_usdt=total_price,
            invoice_id=invoice.invoice_id,
        )

    await callback.message.edit_text(
        texts.invoice_created(),
        reply_markup=keyboards.pay_invoice(invoice.bot_invoice_url, invoice.invoice_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("check_invoice:"))
async def check_invoice(callback: CallbackQuery) -> None:
    invoice_id = int(callback.data.split(":", 1)[1])

    async with async_session() as session:
        purchase = await get_purchase_by_invoice(session, invoice_id)
        if purchase is None:
            await callback.answer("Заказ не найден", show_alert=True)
            return

        if purchase.status in ("delivered",):
            await callback.answer("Звёзды уже отправлены ✅", show_alert=True)
            return

        status = await cryptopay_service.get_invoice_status(invoice_id)
        if status != "paid":
            await callback.answer(texts.payment_not_found(), show_alert=True)
            return

        if purchase.status == "pending":
            await mark_purchase(session, purchase, "paid")

        settings = await get_settings(session)

    await callback.answer()
    await callback.message.edit_text("⏳ Оплата найдена, покупаю звёзды…")

    try:
        result = await fragment_service.buy_stars(purchase.recipient_username, purchase.stars_amount)
        async with async_session() as session:
            purchase = await get_purchase_by_invoice(session, invoice_id)
            await mark_purchase(session, purchase, "delivered", fragment_transaction_id=str(result.transaction_id))
        await callback.message.answer(
            texts.purchase_delivered(settings.message_after_purchase),
            parse_mode="HTML",
        )
    except FragmentError as exc:
        logger.warning("Покупка не удалась для инвойса %s: %s", invoice_id, exc)
        async with async_session() as session:
            purchase = await get_purchase_by_invoice(session, invoice_id)
            await mark_purchase(session, purchase, "failed")
        await callback.message.answer(texts.purchase_failed(str(exc)), parse_mode="HTML")
    except Exception:
        logger.exception("Неожиданная ошибка при покупке звёзд по инвойсу %s", invoice_id)
        async with async_session() as session:
            purchase = await get_purchase_by_invoice(session, invoice_id)
            await mark_purchase(session, purchase, "failed")
        await callback.message.answer(texts.purchase_failed("внутренняя ошибка бота"), parse_mode="HTML")
