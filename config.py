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
MAX_STARS: int = int(os.getenv("MAX_STARS", "1000000"))

# Начальная цена за 1 звезду в USDT (потом меняется из админки, хранится в БД)
DEFAULT_PRICE_PER_STAR_USDT: float = float(os.getenv("DEFAULT_PRICE_PER_STAR_USDT", "0.015"))

# Сколько минут ждать оплату инвойса, прежде чем считать его просроченным
INVOICE_EXPIRES_MINUTES: int = int(os.getenv("INVOICE_EXPIRES_MINUTES", "20"))
