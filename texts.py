import config
from utils.emoji import emoji


def welcome() -> str:
    return (
        f"{emoji('welcome')} Добро пожаловать!\n"
        f"<blockquote>{emoji('zap')}Покупайте Звезды и Premium по самым низким ценам.</blockquote>\n\n"
        f"{emoji('gift')} Выдача товаров моментальна!"
    )


def stars_type() -> str:
    return f"{emoji('gift_star')}  Введите юзернейм кому отправить звезды (пример: @username/username):"


def premium_type() -> str:
    return f"{emoji('gift_star')}  Введите юзернейм кому отправить премиум (пример: @username/username):"


def choose_premium_months(username: str) -> str:
    return f"Выберите вариант подписки"


def premium_price_confirm(months: int, total_rub) -> str:
    return f"Вы покупаете Telegram Premium на {months} мес.\n\n{emoji('check')} Стоимость: {round(float(total_rub))} ₽\n\n{emoji('dollar')}Выберите метод оплаты "


def premium_invoice_message(username: str, months: int, total_rub: int) -> str:
    return (
        f"{emoji('schet')} Счёт CryptoBot\n\n"
        f"{emoji('polychatel')}Получатель: @{username}\n"
        f"{emoji('premium')}Товар: Premium {months} мес.\n"
        f"{emoji('check')}Сумма: {total_rub}₽\n\n"
        f"<blockquote>{emoji('znak')} После успешной оплаты бот автоматически обработает ваш заказ</blockquote>"
    )


def profile(tg_id: int, joined_at, total_stars: int, approx_usd: float) -> str:
    joined_str = joined_at.strftime("%Y-%m-%d") if joined_at else "-"
    return (
        f"👤 <b>Личный кабинет</b>\n\n"
        f"🆔 Твой ID: <code>{tg_id}</code>\n"
        f"🌐 В боте с: {joined_str}\n\n"
        f"За это время вами приобретено {total_stars} ⭐ (~{approx_usd:.1f}$)"
    )


def no_username_error() -> str:
    return (
        "❗️У вас не установлен @username.\n\n"
        "‼️Вам нужно перейти в «Настройки» — «Мой аккаунт» — «Имя пользователя». "
        "Далее установите желаемый @username и повторите попытку."
    )


def ask_recipient_username() -> str:
    return "Введите @username получателя:"


def checking_username() -> str:
    return "🔎 Проверяю юзернейм…"


def username_not_found(username: str) -> str:
    return f"❌ Пользователь @{username} не найден в Telegram. Проверьте юзернейм и попробуйте снова."


def choose_amount(username: str) -> str:
    return f"Введите количество Stars для @{username} (минимум {config.MIN_STARS}, максимум {config.MAX_STARS} за раз)"


def not_integer_error() -> str:
    return "Введите целое число."


def amount_out_of_range_error(username: str) -> str:
    return f"Введите сумму от {config.MIN_STARS} до {config.MAX_STARS} звёзд для @{username}"


def price_confirm(amount: int, total_rub) -> str:
    return f"Вы покупаете {amount}{emoji('star')} \n\n{emoji('сheck')}Стоимость: {round(float(total_rub))} ₽\n\n{emoji('dollar')}Выберите счёт для оплаты"


def invoice_message(username: str, amount: int, total_rub: int) -> str:
    return (
        f"{emoji('schet')} Счёт CryptoBot\n\n"
        f"{emoji('polychatel')}Получатель: @{username}\n"
        f"{emoji('premium')}Товар: {amount} ⭐️\n"
        f"{emoji('check')}Сумма: {total_rub}₽\n\n"
        f"<blockquote>{emoji('znak')} После успешной оплаты бот автоматически обработает ваш заказ</blockquote>"
    )


def purchase_delivered(default_message: str) -> str:
    return f"{emoji('check')} {default_message}"


def purchase_failed(reason: str) -> str:
    return (
        f"{emoji('cross')} Оплата получена, но при покупке звёзд произошла ошибка:\n"
        f"<code>{reason}</code>\n\n"
        f"Напишите в поддержку — вам помогут: @{config.SUPPORT_USERNAME}"
    )


def maintenance_message() -> str:
    return "🛠 Ведутся технические работы. Пожалуйста, зайдите чуть позже."


# --- Админка ---


def admin_menu_header() -> str:
    return f"{emoji('admin')} <b>Меню администратора</b>\n<i>Здесь вы можете настраивать своего бота</i>"


def admin_stats_empty() -> str:
    return f"{emoji('stats')} <b>Статистика</b>\n\nПокупок пока нет."


def admin_stats_entry(purchase) -> str:
    buyer = f"@{purchase.buyer_username}" if purchase.buyer_username else "None"
    when = purchase.paid_at or purchase.created_at
    when_str = when.strftime("%d.%m.%Y %H:%M")
    return (
        f"ID-{purchase.user_tg_id}\n"
        f"User-{buyer}\n"
        f"Купил-{purchase.stars_amount}\n"
        f"дата время-{when_str}\n"
        f"кому-@{purchase.recipient_username}"
    )


def maintenance_status(enabled: bool) -> str:
    return "🛠 Тех.работы: ВКЛ" if enabled else "🛠 Тех.работы: ВЫКЛ"


def markup_menu(price_per_star_rub) -> str:
    return (
        f"{emoji('markup')} <b>Наценки</b>\n\n"
        f"Текущая цена: <b>{price_per_star_rub} ₽</b> за 1 звезду\n\n"
        f"Отправьте новое число (например 1.3), чтобы изменить цену."
    )


def premium_markup_menu(months: int, current_price_rub) -> str:
    return (
        f"{emoji('markup')} <b>Наценки Premium — {months} мес.</b>\n\n"
        f"Текущая цена: <b>{current_price_rub} ₽</b> за весь срок ({months} мес.)\n\n"
        f"Отправьте новое число (например 1200), чтобы изменить цену."
    )


def premium_markup_choice() -> str:
    return f"{emoji('markup')} <b>Наценки Premium</b>\n\nВыберите срок, для которого хотите изменить цену:"


def markup_choice() -> str:
    return f"{emoji('markup')} <b>Наценки</b>\n\nЧто хотите изменить?"


def broadcast_prompt() -> str:
    return f"{emoji('broadcast')} Отправьте сообщение (текст/фото/видео с подписью), которое разослать всем пользователям."


def broadcast_confirm(recipients: int) -> str:
    return f"Разослать это сообщение {recipients} пользователям?"


def broadcast_done(sent: int, failed: int) -> str:
    return f"{emoji('check')} Рассылка завершена.\nОтправлено: {sent}\nНе удалось: {failed}"


def message_after_purchase_prompt(current: str) -> str:
    return f"Текущее сообщение после покупки:\n\n{current}\n\nОтправьте новый текст, чтобы изменить."
