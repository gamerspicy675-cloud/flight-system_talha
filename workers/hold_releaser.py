import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, and_
from app.core.database import get_session_factory
from app.models.flight import SeatInventory
from app.models.booking import Booking, BookingStatus

async def sweep_expired_holds():
    async with get_session_factory()() as db:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Booking)
            .where(and_(Booking.status == BookingStatus.HELD, Booking.hold_expires_at <= now))
            .with_for_update(skip_locked=True)
        )
        bookings = (await db.execute(stmt)).scalars().all()
        for b in bookings:
            inv = await db.scalar(
                select(SeatInventory)
                .where(SeatInventory.flight_id == b.flight_id, SeatInventory.travel_class == b.travel_class)
                .with_for_update()
            )
            if inv:
                inv.held_seats = max(0, inv.held_seats - 1)
                inv.available_seats += 1
            b.status = BookingStatus.CANCELLED
            print(f"[RELEASER] Swept expired hold: Booking {b.id}")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(sweep_expired_holds())
