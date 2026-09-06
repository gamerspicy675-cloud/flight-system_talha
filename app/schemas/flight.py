import uuid
from datetime import datetime
from pydantic import BaseModel, Field, model_validator
from app.models.flight import SeatClass
from app.models.booking import FareType, BookingStatus

# Seat Inventory Input
class SeatInventoryCreate(BaseModel):
    travel_class: SeatClass
    total_seats: int = Field(gt=0, description="Seats must be positive integer")
    base_price: float = Field(gt=0, description="Base price must be greater than zero")

# Admin Create Flight
class FlightCreate(BaseModel):
    flight_number: str = Field(min_length=3, max_length=10)
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_time: datetime
    arrival_time: datetime
    total_capacity: int = Field(gt=0)
    seat_allocations: list[SeatInventoryCreate]

    @model_validator(mode="after")
    def validate_capacity_and_dates(self):
        if self.arrival_time <= self.departure_time:
            raise ValueError("arrival_time must be after departure_time")
        
        allocated_seats = sum(item.total_seats for item in self.seat_allocations)
        if allocated_seats != self.total_capacity:
            raise ValueError(
                f"Seat allocations ({allocated_seats}) must match total capacity ({self.total_capacity})"
            )
        return self

# Flight Response Schema
class SeatInventoryRead(BaseModel):
    travel_class: SeatClass
    total_seats: int
    available_seats: int
    held_seats: int
    base_price: float

    class Config:
        from_attributes = True

class FlightRead(BaseModel):
    id: uuid.UUID
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_capacity: int
    status: str
    inventories: list[SeatInventoryRead]

    class Config:
        from_attributes = True
