import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import (
    Booking,
    BookingStatus,
    FareType,
    WaitlistEntry,
    WaitlistStatus,
)
from app.models.flight import Flight, SeatClass, SeatInventory
from app.schemas.booking import (
    SeatHoldRequest,
    WaitlistRequest,
)
from app.schemas.flight import FlightCreate


class InventoryService:

    @staticmethod
    async def create_flight(db: AsyncSession, data: FlightCreate) -> Flight:
        flight = Flight(
            flight_number=data.flight_number.upper(),
            origin=data.origin.upper(),
            destination=data.destination.upper(),
            departure_time=data.departure_time,
            arrival_time=data.arrival_time,
            total_capacity=data.total_capacity,
        )
        db.add(flight)
        await db.flush()

        for alloc in data.seat_allocations:
            inventory = SeatInventory(
                flight_id=flight.id,
                travel_class=alloc.travel_class,
                total_seats=alloc.total_seats,
                available_seats=alloc.total_seats,
                held_seats=0,
                base_price=alloc.base_price,
            )
            db.add(inventory)

        await db.commit()
        await db.refresh(flight, ["inventories"])
        return flight

    @staticmethod
    async def hold_seat(
        db: AsyncSession,
        request: SeatHoldRequest,
        idempotency_key: str,
    ) -> Booking:
        # 1. Check idempotency: Return existing record if already handled
        existing_booking = await db.scalar(
            select(Booking).where(Booking.idempotency_key == idempotency_key)
        )
        if existing_booking:
            return existing_booking

        # 2. Acquire a row-level lock on the specific inventory bucket
        stmt = (
            select(SeatInventory)
            .where(
                SeatInventory.flight_id == request.flight_id,
                SeatInventory.travel_class == request.travel_class,
            )
            .with_for_update()  # SELECT ... FOR UPDATE
        )
        result = await db.execute(stmt)
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Seat inventory class not found for this flight",
            )

        if inventory.available_seats <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No available seats in requested class",
            )

        # 3. Decrement available seats and increment held seats atomically
        inventory.available_seats -= 1
        inventory.held_seats += 1

        # 4. Create the provisional booking record
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=request.hold_duration_minutes
        )
        booking = Booking(
            flight_id=request.flight_id,
            passenger_name=request.passenger_name,
            passenger_email=request.passenger_email,
            travel_class=request.travel_class,
            fare_type=request.fare_type,
            status=BookingStatus.HELD,
            idempotency_key=idempotency_key,
            hold_expires_at=expires_at,
            total_paid=inventory.base_price,
        )

        db.add(booking)
        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def confirm_booking(db: AsyncSession, booking_id: uuid.UUID) -> Booking:
        booking = await db.scalar(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.status != BookingStatus.HELD:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm booking in status {booking.status}",
            )

        if booking.hold_expires_at and datetime.now(timezone.utc) > booking.hold_expires_at:
            # Expired hold: release held seat back to available
            inv = await db.scalar(
                select(SeatInventory)
                .where(
                    SeatInventory.flight_id == booking.flight_id,
                    SeatInventory.travel_class == booking.travel_class,
                )
                .with_for_update()
            )
            if inv:
                inv.held_seats = max(0, inv.held_seats - 1)
                inv.available_seats += 1
            booking.status = BookingStatus.CANCELLED
            await db.commit()
            raise HTTPException(status_code=400, detail="Seat hold has expired")

        # Confirm booking: convert held seat to permanently booked
        inv = await db.scalar(
            select(SeatInventory)
            .where(
                SeatInventory.flight_id == booking.flight_id,
                SeatInventory.travel_class == booking.travel_class,
            )
            .with_for_update()
        )
        if inv:
            inv.held_seats = max(0, inv.held_seats - 1)

        booking.status = BookingStatus.CONFIRMED
        await db.commit()
        await db.refresh(booking)
        return booking

    @staticmethod
    async def cancel_booking(db: AsyncSession, booking_id: uuid.UUID) -> dict:
        booking = await db.scalar(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.status in (BookingStatus.CANCELLED, BookingStatus.REFUNDED):
            raise HTTPException(
                status_code=400, detail="Booking is already cancelled/refunded"
            )

        # Fare cancellation rules
        refund_amount = 0.0
        credit_amount = 0.0
        if booking.fare_type == FareType.REFUNDABLE:
            refund_amount = float(booking.total_paid)
            booking.status = BookingStatus.REFUNDED
        elif booking.fare_type == FareType.FLEXIBLE:
            credit_amount = float(booking.total_paid) * 0.9  # 10% cancellation fee, 90% credit
            booking.status = BookingStatus.CANCELLED
        else:  # BASIC_ECONOMY
            booking.status = BookingStatus.CANCELLED  # No refund, no credit

        # Restore inventory
        inv = await db.scalar(
            select(SeatInventory)
            .where(
                SeatInventory.flight_id == booking.flight_id,
                SeatInventory.travel_class == booking.travel_class,
            )
            .with_for_update()
        )
        if inv:
            inv.available_seats += 1

        await db.commit()
        return {
            "booking_id": str(booking.id),
            "status": booking.status.value,
            "fare_type": booking.fare_type.value,
            "refund_amount": refund_amount,
            "travel_credit": credit_amount,
        }

    @staticmethod
    async def join_waitlist(db: AsyncSession, data: WaitlistRequest) -> WaitlistEntry:
        # Calculate priority: VIP: 100, GOLD: 50, SILVER: 25, STANDARD: 0
        tier_weight = {
            "VIP": 100,
            "GOLD": 50,
            "SILVER": 25,
            "STANDARD": 0,
        }.get(data.loyalty_tier.upper(), 0)

        entry = WaitlistEntry(
            flight_id=data.flight_id,
            passenger_name=data.passenger_name,
            passenger_email=data.passenger_email,
            travel_class=data.travel_class,
            loyalty_tier=data.loyalty_tier.upper(),
            priority_score=tier_weight,
            status=WaitlistStatus.PENDING,
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry