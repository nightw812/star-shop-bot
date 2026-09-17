import asyncio
import logging
import re

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyfragment import FragmentError

import config
from fragment_service import buy_stars, check_wallet_balance

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

router = Router()

# Только владелец бота (OWNER_ID из .env) может им пользоваться
router.message.filter(F.from_user.id == config.OWNER_ID)
router.callback_query.filter(F.from_user.id == config.OWNER_ID)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{5,32}$")


class BuyStars(StatesGroup):
    waiting_username = State()
    waiting_amount = State()
    waiting_confirm = State()


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить покупку", callback_data="confirm_buy"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_buy"),
            ]
        ]
    )


def normalize_username(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("https://t.me/"):
        raw = raw.split("https://t.me/", 1)[1]
    return raw.lstrip("@").strip()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Привет! Я куплю Telegram Stars через Fragment на твой TON-кошелёк.\n\n"
        "Команды:\n"
        "/buy — купить звёзды\n"
        "/balance — баланс подключённого TON-кошелька\n"
        "/cancel — отменить текущую операцию"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Операция отменена.")


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    msg = await message.answer("Проверяю баланс кошелька…")
    try:
        gram, usdt = await check_wallet_balance()
        await msg.edit_text(f"💰 Баланс кошелька:\nTON: {gram}\nUSDT: {usdt}")
    except FragmentError as exc:
        await msg.edit_text(f"⚠️ Не удалось получить баланс: {exc}")
    except Exception:
        logger.exception("Неожиданная ошибка при получении баланса")
        await msg.edit_text("⚠️ Неожиданная ошибка при получении баланса. Смотри логи.")


@router.message(Command("buy"))
async def cmd_buy(message: Message, state: FSMContext) -> None:
    await state.set_state(BuyStars.waiting_username)
    await message.answer(
        "Введи юзернейм получателя (например, durov или @durov, или ссылку https://t.me/durov):"
    )


@router.message(BuyStars.waiting_username)
async def process_username(message: Message, state: FSMContext) -> None:
    username = normalize_username(message.text or "")
    if not USERNAME_RE.match(username):
        await message.answer(
            "Юзернейм выглядит некорректно (5-32 символа, латиница/цифры/_). Попробуй ещё раз, или /cancel."
        )
        return

    await state.update_data(username=username)
    await state.set_state(BuyStars.waiting_amount)
    await message.answer(
        f"Получатель: @{username}\n\n"
        f"Сколько звёзд купить? (целое число от {config.MIN_STARS} до {config.MAX_STARS})"
    )


@router.message(BuyStars.waiting_amount)
async def process_amount(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().replace(" ", "")
    if not text.isdigit():
        await message.answer("Нужно целое число. Попробуй ещё раз, или /cancel.")
        return

    amount = int(text)
    if not (config.MIN_STARS <= amount <= config.MAX_STARS):
        await message.answer(
            f"Количество должно быть от {config.MIN_STARS} до {config.MAX_STARS}. Попробуй ещё раз, или /cancel."
        )
        return

    data = await state.update_data(amount=amount)
    await state.set_state(BuyStars.waiting_confirm)
    await message.answer(
        f"Подтверди покупку:\n\n"
        f"Получатель: @{data['username']}\n"
        f"Количество звёзд: {amount}\n\n"
        f"Оплата спишется с твоего TON-кошелька.",
        reply_markup=confirm_keyboard(),
    )


@router.callback_query(BuyStars.waiting_confirm, F.data == "cancel_buy")
async def cancel_buy(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Покупка отменена.")
    await callback.answer()


@router.callback_query(BuyStars.waiting_confirm, F.data == "confirm_buy")
async def confirm_buy(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    username = data["username"]
    amount = data["amount"]
    await state.clear()

    await callback.message.edit_text(f"⏳ Покупаю {amount} звёзд для @{username}…")
    await callback.answer()

    try:
        result = await buy_stars(username, amount)
        await callback.message.answer(
            "✅ Готово!\n\n"
            f"Получатель: @{result.username}\n"
            f"Звёзд куплено: {result.amount}\n"
            f"ID транзакции: {result.transaction_id}"
        )
    except FragmentError as exc:
        logger.warning("Покупка не удалась: %s", exc)
        await callback.message.answer(f"❌ Не удалось купить звёзды: {exc}")
    except Exception:
        logger.exception("Неожиданная ошибка при покупке звёзд")
        await callback.message.answer("❌ Неожиданная ошибка при покупке. Смотри логи бота.")


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Не понял. Используй /buy, чтобы купить звёзды, или /balance для проверки баланса.")


async def main() -> None:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
