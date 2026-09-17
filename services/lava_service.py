"""
Интеграция с LAVA BUSINESS (https://dev.lava.ru) — приём оплаты через СБП.

Подтверждено из официальной документации и исходников открытых SDK (SKitLs.Payments.Lava,
lava-business npm), которые прямо ссылаются на dev.lava.ru:

- Базовый URL: https://api.lava.ru/business
- POST /invoice/create — body: {sum, orderId, shopId, hookUrl?, successUrl?, failUrl?, expire?, customFields?}
- POST /invoice/status — body: {shopId, orderId} ИЛИ {shopId, invoiceId}
- Подпись: HMAC-SHA256(secret_key, raw_json_body) в hex (lowercase), передаётся в заголовке "Signature".
  JSON тела должен быть СЕРИАЛИЗОВАН РОВНО В ТОМ ЖЕ ВИДЕ, что подписывался (тот же порядок полей).

⚠️ Точный формат ОТВЕТА сервера (какие именно ключи в JSON) не задокументирован в открытом
виде (рендерится через Swagger UI на JS) — здесь сделан гибкий разбор нескольких вероятных
вариантов. Если парсинг не сработает с реальным аккаунтом — пришли сырой ответ, поправим за
пару минут: структура запроса и подписи гарантированно верна, под вопросом только response.
"""

import hashlib
import hmac
import json
import logging
from decimal import Decimal
from typing import Any

import httpx

import config

logger = logging.getLogger(__name__)


class LavaError(Exception):
    pass


def _sign(json_body: str) -> str:
    return hmac.new(
        config.LAVA_SECRET_KEY.encode("utf-8"),
        json_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    # Сериализуем один раз и подписываем ИМЕННО эту строку — порядок ключей должен совпадать
    # с тем, что отправляется в теле (сортировку/пересборку JSON после подписи не делаем).
    body = json.dumps(payload, ensure_ascii=False)
    signature = _sign(body)

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Signature": signature,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{config.LAVA_BASE_URL}{path}", content=body.encode("utf-8"), headers=headers)

    try:
        data = response.json()
    except ValueError as exc:
        raise LavaError(f"Lava вернула не-JSON ответ ({response.status_code}): {response.text[:300]}") from exc

    if response.status_code >= 400:
        raise LavaError(f"Lava HTTP {response.status_code}: {data}")

    return data


def _extract(data: dict[str, Any], *keys: str) -> Any:
    """Достаёт значение из data напрямую или из вложенного data['data'] — под разные
    варианты обёртки ответа."""
    for key in keys:
        if key in data:
            return data[key]
    nested = data.get("data")
    if isinstance(nested, dict):
        for key in keys:
            if key in nested:
                return nested[key]
    return None


async def create_invoice(order_id: str, amount_rub: Decimal, comment: str = "") -> dict[str, str]:
    """Создаёт счёт на оплату (СБП/карта через LAVA). Возвращает {"invoice_id":..., "url":...}."""
    payload = {
        "sum": float(amount_rub),
        "orderId": order_id,
        "shopId": config.LAVA_SHOP_ID,
    }
    if comment:
        payload["customFields"] = comment[:500]

    data = await _post("/invoice/create", payload)

    url = _extract(data, "url")
    invoice_id = _extract(data, "id", "invoice_id", "invoiceId")

    if not url:
        raise LavaError(f"Не удалось получить ссылку на оплату из ответа Lava: {data}")

    return {"invoice_id": str(invoice_id) if invoice_id else order_id, "url": url}


async def get_invoice_status(order_id: str) -> str:
    """Возвращает статус счёта. Нормализуем к: pending | paid | failed | expired."""
    payload = {"shopId": config.LAVA_SHOP_ID, "orderId": order_id}
    data = await _post("/invoice/status", payload)

    raw_status = str(_extract(data, "status") or "").lower()

    if raw_status in ("success", "paid", "completed", "confirmed"):
        return "paid"
    if raw_status in ("expired", "cancel", "cancelled", "canceled"):
        return "expired"
    if raw_status in ("error", "failed", "fail"):
        return "failed"
    return "pending"
