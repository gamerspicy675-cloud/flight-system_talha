import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.flight import SeatClass
from app.models.booking import FareType, BookingStatus

class SeatHoldRequest(BaseModel):
    flight_id: uuid.UUID
    passenger_name: str = Field(min_length=2)
    passenger_email: EmailStr
    travel_class: SeatClass
    fare_type: FareType
    hold_duration_minutes: int = Field(default=10, le=30)

class SeatHoldResponse(BaseModel):
    booking_id: uuid.UUID
    flight_id: uuid.UUID
    passenger_name: str
    travel_class: SeatClass
    fare_type: FareType
    status: BookingStatus
    hold_expires_at: datetime
    total_price: float
    idempotency_key: str

    class Config:
        from_attributes = True

class BookingConfirmRequest(BaseModel):
    booking_id: uuid.UUID
    payment_reference: str

class BookingCancelRequest(BaseModel):
    booking_id: uuid.UUID
    reason: str = "Customer requested"

class WaitlistRequest(BaseModel):
    flight_id: uuid.UUID
    passenger_name: str = Field(min_length=2)
    passenger_email: EmailStr
    travel_class: SeatClass
    loyalty_tier: str = "STANDARD"  # STANDARD, SILVER, GOLD, VIP       