import logging

from pyfragment import FragmentClient, PremiumResult, StarsResult
from pyfragment.core.constants import STARS_PAGE

import config

logger = logging.getLogger(__name__)


def _client() -> FragmentClient:
    return FragmentClient(
        seed=config.TON_SEED,
        api_key=config.TONAPI_KEY,
        cookies=config.FRAGMENT_COOKIES,
        wallet_version=config.WALLET_VERSION,
        api_provider=config.API_PROVIDER,
    )


async def check_username_exists(username: str) -> bool:
    """Проверяет через Fragment, существует ли такой пользователь Telegram."""
    async with _client() as client:
        result = await client.call("searchStarsRecipient", {"query": username, "quantity": ""}, page_url=STARS_PAGE)
        if "assigned to a user" in str(result.get("error", "")).lower():
            return False
        recipient = result.get("found", {}).get("recipient")
        return bool(recipient)


async def buy_stars(username: str, amount: int) -> StarsResult:
    async with _client() as client:
        logger.info("Покупка %s звёзд для %s (аноним=%s)", amount, username, config.ANONYMOUS_PURCHASES)
        result = await client.purchase_stars(username, amount, show_sender=not config.ANONYMOUS_PURCHASES)
        logger.info("Готово: %s", result)
        return result


async def buy_premium(username: str, months: int) -> PremiumResult:
    async with _client() as client:
        logger.info("Покупка Premium на %s мес. для %s (аноним=%s)", months, username, config.ANONYMOUS_PURCHASES)
        result = await client.purchase_premium(username, months, show_sender=not config.ANONYMOUS_PURCHASES)
        logger.info("Готово: %s", result)
        return result


async def check_wallet_balance() -> tuple[float, float]:
    async with _client() as client:
        wallet = await client.get_wallet()
        return wallet.gram_balance, wallet.usdt_balance
