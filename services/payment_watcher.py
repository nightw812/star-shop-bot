import asyncio
import logging

from aiogram import Bot
from pyfragment import FragmentError

import config
import texts
from database import (
    Purchase,
    async_session,
    get_pending_purchases,
    get_purchase_by_invoice,
    get_settings,
    mark_purchase,
)
from services import cryptopay_service, fragment_service, lava_service

logger = logging.getLogger(__name__)


async def _handle_paid(bot: Bot, invoice_id: int) -> None:
    async with async_session() as session:
        purchase = await get_purchase_by_invoice(session, invoice_id)
        if purchase is None or purchase.status != "pending":
            return
        await mark_purchase(session, purchase, "paid")
        recipient = purchase.recipient_username
        amount = purchase.stars_amount
        product = purchase.product
        buyer_chat_id = purchase.user_tg_id

    try:
        if product == "premium":
            result = await fragment_service.buy_premium(recipient, amount)
        else:
            result = await fragment_service.buy_stars(recipient, amount)
    except FragmentError as exc:
        logger.warning("Покупка не удалась для инвойса %s: %s", invoice_id, exc)
        async with async_session() as session:
            purchase = await get_purchase_by_invoice(session, invoice_id)
            await mark_purchase(session, purchase, "failed")
        await bot.send_message(buyer_chat_id, texts.purchase_failed(str(exc)), parse_mode="HTML")
        return
    except Exception:
        logger.exception("Неожиданная ошибка при покупке звёзд по инвойсу %s", invoice_id)
        async with async_session() as session:
            purchase = await get_purchase_by_invoice(session, invoice_id)
            await mark_purchase(session, purchase, "failed")
        await bot.send_message(buyer_chat_id, texts.purchase_failed("внутренняя ошибка бота"), parse_mode="HTML")
        return

    async with async_session() as session:
        purchase = await get_purchase_by_invoice(session, invoice_id)
        await mark_purchase(session, purchase, "delivered", fragment_transaction_id=str(result.transaction_id))
        settings = await get_settings(session)

    await bot.send_message(buyer_chat_id, texts.purchase_delivered(settings.message_after_purchase), parse_mode="HTML")


async def poll_payments(bot: Bot) -> None:
    logger.info("Запущена фоновая проверка оплат (каждые %s сек.)", config.PAYMENT_POLL_INTERVAL_SECONDS)
    while True:
        try:
            async with async_session() as session:
                pending: list[Purchase] = await get_pending_purchases(session)

            for purchase in pending:
                try:
                    if purchase.payment_provider == "lava":
                        status = await lava_service.get_invoice_status(purchase.invoice_id)
                    else:
                        status = await cryptopay_service.get_invoice_status(int(purchase.invoice_id))
                except Exception:
                    logger.exception("Не удалось получить статус инвойса %s", purchase.invoice_id)
                    continue

                if status == "paid":
                    await _handle_paid(bot, purchase.invoice_id)
                elif status == "expired":
                    async with async_session() as session:
                        fresh = await get_purchase_by_invoice(session, purchase.invoice_id)
                        if fresh and fresh.status == "pending":
                            await mark_purchase(session, fresh, "expired")
        except Exception:
            logger.exception("Ошибка в фоновом цикле проверки оплат")

        await asyncio.sleep(config.PAYMENT_POLL_INTERVAL_SECONDS)
