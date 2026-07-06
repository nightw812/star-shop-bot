import os

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {name} — проверь файл .env")
    return value


def _int_list(name: str) -> list[int]:
    raw = os.getenv(name, "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


# Токен бота-магазина от @BotFather
BOT_TOKEN: str = _required("BOT_TOKEN")

# Список Telegram user_id админов через запятую, например: 111111,222222
ADMIN_IDS: list[int] = _int_list("ADMIN_IDS")

# --- База данных (PostgreSQL) ---
# Формат: postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL: str = _required("DATABASE_URL")

# --- CryptoBot (@CryptoBot / @send) ---
# Получить в @CryptoBot -> Crypto Pay -> Create App
CRYPTOBOT_TOKEN: str = _required("CRYPTOBOT_TOKEN")
# Тестовая сеть @CryptoTestnetBot или боевая @CryptoBot
CRYPTOBOT_TESTNET: bool = os.getenv("CRYPTOBOT_TESTNET", "false").lower() == "true"

# --- Fragment / TON (см. предыдущую версию бота) ---
TON_SEED: str = _required("TON_SEED")
WALLET_VERSION: str = os.getenv("WALLET_VERSION", "V5R1")
TONAPI_KEY: str = _required("TONAPI_KEY")
API_PROVIDER: str = os.getenv("API_PROVIDER", "tonapi")

import json  # noqa: E402

_raw_cookies = _required("FRAGMENT_COOKIES")
try:
    FRAGMENT_COOKIES: dict = json.loads(_raw_cookies)
except json.JSONDecodeError as exc:
    raise RuntimeError(
        "FRAGMENT_COOKIES должен быть валидным JSON, например: "
        '{"stel_ssid": "...", "stel_dt": "...", "stel_token": "...", "stel_ton_token": "..."}'
    ) from exc

# --- Магазин ---
SUPPORT_USERNAME: str = os.getenv("SUPPORT_USERNAME", "Night_supp")
MIN_STARS: int = int(os.getenv("MIN_STARS", "50"))
MAX_STARS: int = int(os.getenv("MAX_STARS", "1000"))

# Начальная цена за 1 звезду в рублях (потом меняется из админки, хранится в БД)
DEFAULT_PRICE_PER_STAR_RUB: float = float(os.getenv("DEFAULT_PRICE_PER_STAR_RUB", "1.25"))

# file_id стикера, который бот присылает по /start.
# Как получить: перешли любой стикер боту @RawDataBot или @getidsbot — он покажет file_id в поле sticker.file_id.
WELCOME_STICKER_ID: str | None = os.getenv("WELCOME_STICKER_ID") or None

# Сколько минут ждать оплату инвойса, прежде чем считать его просроченным
INVOICE_EXPIRES_MINUTES: int = int(os.getenv("INVOICE_EXPIRES_MINUTES", "20"))

# Как часто (в секундах) фоновая задача проверяет неоплаченные инвойсы
PAYMENT_POLL_INTERVAL_SECONDS: int = int(os.getenv("PAYMENT_POLL_INTERVAL_SECONDS", "7"))

# Скрывать ли отправителя при покупке звёзд/Premium на Fragment (анонимная покупка)
ANONYMOUS_PURCHASES: bool = os.getenv("ANONYMOUS_PURCHASES", "true").lower() == "true"

# Комиссия CryptoBot, накидывается на сумму именно в момент создания счёта на оплату (в %)
CRYPTOBOT_FEE_PERCENT: float = float(os.getenv("CRYPTOBOT_FEE_PERCENT", "3.1"))

# Стартовые цены Premium по тарифам (в рублях), меняются из админки
DEFAULT_PREMIUM_PRICES: dict[int, float] = {3: 1200.0, 6: 1300.0, 12: 2400.0}
PREMIUM_MONTH_OPTIONS: list[int] = [3, 6, 12]
