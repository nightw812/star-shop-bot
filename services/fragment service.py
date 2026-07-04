import logging

from pyfragment import FragmentClient, FragmentError, StarsResult

import config

logger = logging.getLogger(__name__)


async def buy_stars(username: str, amount: int) -> StarsResult:
    """
    Покупает `amount` звёзд для пользователя `username` через Fragment,
    оплачивая TON-кошельком, заданным в config.TON_SEED.

    Кидает pyfragment.FragmentError (или его подклассы) при любой ошибке —
    их текст уже человекочитаемый и его можно показывать пользователю бота.
    """
    async with FragmentClient(
        seed=config.TON_SEED,
        api_key=config.TONAPI_KEY,
        cookies=config.FRAGMENT_COOKIES,
        wallet_version=config.WALLET_VERSION,
        api_provider=config.API_PROVIDER,
    ) as client:
        logger.info("Покупка %s звёзд для %s", amount, username)
        result = await client.purchase_stars(username, amount)
        logger.info("Готово: %s", result)
        return result


async def check_wallet_balance() -> tuple[float, float]:
    """Возвращает (баланс TON, баланс USDT) кошелька."""
    async with FragmentClient(
        seed=config.TON_SEED,
        api_key=config.TONAPI_KEY,
        cookies=config.FRAGMENT_COOKIES,
        wallet_version=config.WALLET_VERSION,
        api_provider=config.API_PROVIDER,
    ) as client:
        wallet = await client.get_wallet()
        return wallet.gram_balance, wallet.usdt_balance
