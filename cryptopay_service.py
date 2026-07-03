from decimal import Decimal

from aiocryptopay import AioCryptoPay, Networks
from aiocryptopay.models.invoice import Invoice

import config

_network = Networks.TEST_NET if config.CRYPTOBOT_TESTNET else Networks.MAIN_NET


def _client() -> AioCryptoPay:
    return AioCryptoPay(token=config.CRYPTOBOT_TOKEN, network=_network)


async def create_invoice(amount_usdt: Decimal, description: str, payload: str) -> Invoice:
    async with _client() as client:
        invoice = await client.create_invoice(
            amount=float(amount_usdt),
            asset="USDT",
            description=description,
            payload=payload,
            expires_in=config.INVOICE_EXPIRES_MINUTES * 60,
        )
        return invoice


async def get_invoice_status(invoice_id: int) -> str:
    """Возвращает статус инвойса: active | paid | expired."""
    async with _client() as client:
        invoices = await client.get_invoices(invoice_ids=invoice_id)
        if invoices is None:
            return "expired"
        invoice = invoices[0] if isinstance(invoices, list) else invoices
        return invoice.status
