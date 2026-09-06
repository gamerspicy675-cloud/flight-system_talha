import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.flight import Flight
from app.schemas.flight import FlightCreate, FlightRead
from app.schemas.booking import SeatHoldRequest, SeatHoldResponse
from app.services.inventory_service import InventoryService

router = APIRouter()

@router.post("/admin/flights", response_model=FlightRead)
async def create_flight(
    data: FlightCreate, 
    db: AsyncSession = Depends(get_db)
):
    return await InventoryService.create_flight(db, data)

@router.get("/flights/search", response_model=list[FlightRead])
async def search_flights(
    origin: str,
    destination: str,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Flight)
        .where(
            Flight.origin == origin.upper(),
            Flight.destination == destination.upper(),
            Flight.status == "SCHEDULED"
        )
        .options(selectinload(Flight.inventories))
    )
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/bookings/hold", response_model=SeatHoldResponse)
async def hold_seat_endpoint(
    request: SeatHoldRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db)
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")
    
    booking = await InventoryService.hold_seat(db, request, idempotency_key)
    
    return SeatHoldResponse(
        booking_id=booking.id,
        flight_id=booking.flight_id,
        passenger_name=booking.passenger_name,
        travel_class=booking.travel_class,
        fare_type=booking.fare_type,
        status=booking.status,
        hold_expires_at=booking.hold_expires_at,
        total_price=float(booking.total_paid),
        idempotency_key=booking.idempotency_key,
    )
from app.schemas.booking import BookingConfirmRequest, BookingCancelRequest, WaitlistRequest
from app.models.booking import WaitlistEntry

@router.post("/bookings/confirm")
async def confirm_booking(data: BookingConfirmRequest, db: AsyncSession = Depends(get_db)):
    booking = await InventoryService.confirm_booking(db, data.booking_id)
    return {"booking_id": booking.id, "status": booking.status, "message": "Booking confirmed"}

@router.post("/bookings/cancel")
async def cancel_booking(data: BookingCancelRequest, db: AsyncSession = Depends(get_db)):
    return await InventoryService.cancel_booking(db, data.booking_id)

@router.post("/waitlist/join")
async def join_waitlist(data: WaitlistRequest, db: AsyncSession = Depends(get_db)):
    entry = await InventoryService.join_waitlist(db, data)
    return {
        "waitlist_id": entry.id,
        "flight_id": entry.flight_id,
        "passenger_name": entry.passenger_name,
        "priority_score": entry.priority_score,
        "status": entry.status
    }