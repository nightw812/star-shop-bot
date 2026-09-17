-- Разово выполнить на своей базе перед запуском обновлённого бота.
-- Меняет invoice_id с числового на строковый тип (нужно для Lava, у которой ID заказа — строка)
-- и добавляет колонку payment_provider, чтобы фоновый опросчик знал, кого спрашивать про статус оплаты.

ALTER TABLE purchases
    ALTER COLUMN invoice_id TYPE VARCHAR(64) USING invoice_id::text;

ALTER TABLE purchases
    ADD COLUMN IF NOT EXISTS payment_provider VARCHAR(16) NOT NULL DEFAULT 'cryptobot';
