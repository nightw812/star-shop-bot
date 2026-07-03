import config
from utils.emoji import emoji


def welcome() -> str:
    return (
        f"{emoji('star')} <b>Магазин Telegram Stars</b>\n\n"
        f"Купи звёзды любому пользователю Telegram по курсу ниже.\n"
        f"Оплата — USDT через @CryptoBot."
    )


def ask_username() -> str:
    return "Введи юзернейм получателя (например, durov или @durov):"


def ask_amount(username: str, price_per_star: float) -> str:
    return (
        f"Получатель: @{username}\n"
        f"Цена: <b>{price_per_star:.4f} USDT</b> за 1 звезду\n\n"
        f"Сколько звёзд купить? (от {config.MIN_STARS} до {config.MAX_STARS})"
    )


def order_summary(username: str, amount: int, total_price: float) -> str:
    return (
        f"{emoji('star')} <b>Проверь заказ</b>\n\n"
        f"Получатель: @{username}\n"
        f"Количество звёзд: {amount}\n"
        f"Итого к оплате: <b>{total_price:.4f} USDT</b>\n\n"
        f"После оплаты звёзды придут автоматически."
    )


def invoice_created() -> str:
    return f"{emoji('hourglass')} Инвойс создан. После оплаты бот сам всё проверит и отправит звёзды."


def payment_not_found() -> str:
    return f"{emoji('cross')} Оплата пока не найдена. Если уже оплатил — подожди немного и нажми проверку ещё раз."


def purchase_delivered(default_message: str) -> str:
    return f"{emoji('check')} {default_message}"


def purchase_failed(reason: str) -> str:
    return (
        f"{emoji('cross')} Оплата получена, но при покупке звёзд произошла ошибка:\n"
        f"<code>{reason}</code>\n\n"
        f"Напиши в поддержку — тебе поможем."
    )


def support_text() -> str:
    return f"{emoji('support')} По всем вопросам пиши сюда: @{config.SUPPORT_USERNAME}"


# --- Админка ---


def admin_menu_header() -> str:
    return f"{emoji('admin')} <b>Меню администратора</b>\n<i>Здесь вы можете настраивать своего бота</i>"


def admin_stats_block(period_label: str, new_users: int, purchases_count: int, stars_sum: int, revenue_usdt) -> str:
    return (
        f"{emoji('stats')} <b>Статистика</b> · {period_label}\n\n"
        f"<b>Новых пользователей:</b> {new_users}\n\n"
        f"┌ Кол-во покупок: {purchases_count}\n"
        f"├ Сумма звёзд: {stars_sum} {emoji('star')}\n"
        f"└ Оплачено (USDT): {revenue_usdt}\n\n"
        f"{emoji('money')} Прибыль (по себестоимости из наценки)"
    )


def markup_menu(price_per_star: float) -> str:
    return (
        f"{emoji('markup')} <b>Наценки</b>\n\n"
        f"Текущая цена: <b>{price_per_star:.4f} USDT</b> за 1 звезду\n\n"
        f"Отправь новое число (например 0.016), чтобы изменить цену."
    )


def broadcast_prompt() -> str:
    return f"{emoji('broadcast')} Отправь сообщение (текст/фото/видео с подписью), которое разослать всем пользователям."


def broadcast_confirm(recipients: int) -> str:
    return f"Разослать это сообщение {recipients} пользователям?"


def broadcast_done(sent: int, failed: int) -> str:
    return f"{emoji('check')} Рассылка завершена.\nОтправлено: {sent}\nНе удалось: {failed}"


def message_after_purchase_prompt(current: str) -> str:
    return (
        f"Текущее сообщение после покупки:\n\n{current}\n\n"
        f"Отправь новый текст, чтобы изменить."
    )
