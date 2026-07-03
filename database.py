import datetime as dt
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import config


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, index=True)
    recipient_username: Mapped[str] = mapped_column(String(64))
    stars_amount: Mapped[int] = mapped_column()
    price_usdt: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    invoice_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    # pending | paid | delivered | failed | expired
    status: Mapped[str] = mapped_column(String(16), default="pending")
    fragment_transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Settings(Base):
    """Единственная строка настроек магазина (наценка/цена, тексты)."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    price_per_star_usdt: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), default=Decimal(str(config.DEFAULT_PRICE_PER_STAR_USDT))
    )
    message_after_purchase: Mapped[str] = mapped_column(
        Text, default="✅ Спасибо за покупку! Звёзды уже отправлены получателю."
    )


engine = create_async_engine(config.DATABASE_URL, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        existing = await session.get(Settings, 1)
        if existing is None:
            session.add(Settings(id=1))
            await session.commit()


async def get_or_create_user(session: AsyncSession, tg_id: int, username: str | None) -> User:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(tg_id=tg_id, username=username)
        session.add(user)
        await session.commit()
    elif user.username != username:
        user.username = username
        await session.commit()
    return user


async def get_settings(session: AsyncSession) -> Settings:
    settings = await session.get(Settings, 1)
    if settings is None:
        settings = Settings(id=1)
        session.add(settings)
        await session.commit()
    return settings


async def create_purchase(
    session: AsyncSession,
    user_tg_id: int,
    recipient_username: str,
    stars_amount: int,
    price_usdt: Decimal,
    invoice_id: int,
) -> Purchase:
    purchase = Purchase(
        user_tg_id=user_tg_id,
        recipient_username=recipient_username,
        stars_amount=stars_amount,
        price_usdt=price_usdt,
        invoice_id=invoice_id,
        status="pending",
    )
    session.add(purchase)
    await session.commit()
    await session.refresh(purchase)
    return purchase


async def mark_purchase(
    session: AsyncSession,
    purchase: Purchase,
    status: str,
    fragment_transaction_id: str | None = None,
) -> None:
    purchase.status = status
    if status == "paid" and purchase.paid_at is None:
        purchase.paid_at = dt.datetime.now(dt.timezone.utc)
    if fragment_transaction_id:
        purchase.fragment_transaction_id = fragment_transaction_id
    await session.commit()


async def get_purchase_by_invoice(session: AsyncSession, invoice_id: int) -> Purchase | None:
    result = await session.execute(select(Purchase).where(Purchase.invoice_id == invoice_id))
    return result.scalar_one_or_none()


async def stats_for_period(session: AsyncSession, since: dt.datetime | None) -> dict:
    user_q = select(func.count(User.id))
    purchase_q = select(
        func.count(Purchase.id),
        func.coalesce(func.sum(Purchase.stars_amount), 0),
        func.coalesce(func.sum(Purchase.price_usdt), 0),
    ).where(Purchase.status.in_(["paid", "delivered"]))

    if since is not None:
        user_q = user_q.where(User.created_at >= since)
        purchase_q = purchase_q.where(Purchase.created_at >= since)

    new_users = (await session.execute(user_q)).scalar_one()
    purchases_count, stars_sum, revenue_usdt = (await session.execute(purchase_q)).one()

    return {
        "new_users": new_users,
        "purchases_count": purchases_count,
        "stars_sum": int(stars_sum),
        "revenue_usdt": Decimal(revenue_usdt),
    }


async def all_user_tg_ids(session: AsyncSession) -> list[int]:
    result = await session.execute(select(User.tg_id))
    return [row[0] for row in result.all()]
