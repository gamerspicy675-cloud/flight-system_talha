import asyncio
from sqlalchemy import select
from app.core.database import get_session_factory
from app.models.flight import SeatInventory
from app.models.booking import WaitlistEntry, WaitlistStatus

async def promote_waitlist():
    async with get_session_factory()() as db:
        inv_stmt = select(SeatInventory).where(SeatInventory.available_seats > 0).with_for_update(skip_locked=True)
        inventories = (await db.execute(inv_stmt)).scalars().all()

        for inv in inventories:
            wl_stmt = (
                select(WaitlistEntry)
                .where(
                    WaitlistEntry.flight_id == inv.flight_id,
                    WaitlistEntry.travel_class == inv.travel_class,
                    WaitlistEntry.status == WaitlistStatus.PENDING
                )
                .order_by(WaitlistEntry.priority_score.desc(), WaitlistEntry.created_at.asc())
                .with_for_update(skip_locked=True)
            )
            entry = (await db.execute(wl_stmt)).scalars().first()
            if entry:
                inv.available_seats -= 1
                inv.held_seats += 1
                entry.status = WaitlistStatus.NOTIFIED
                print(f"[PROMOTER] Promoted {entry.passenger_name} ({entry.passenger_email}) on flight {inv.flight_id}")
        await db.commit()

if __name__ == "__main__":
    asyncio.run(promote_waitlist())
