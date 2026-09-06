import uuid
from datetime import datetime
import enum
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.booking import Booking, WaitlistEntry

class SeatClass(str, enum.Enum):
    ECONOMY = "ECONOMY"
    BUSINESS = "BUSINESS"
    FIRST = "FIRST"

class Flight(Base):
    __tablename__ = "flights"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_number: Mapped[str] = mapped_column(String(10), nullable=False)
    origin: Mapped[str] = mapped_column(String(3), nullable=False)
    destination: Mapped[str] = mapped_column(String(3), nullable=False)
    departure_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    inventories: Mapped[list["SeatInventory"]] = relationship(back_populates="flight", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="flight")
    waitlist_entries: Mapped[list["WaitlistEntry"]] = relationship(back_populates="flight")

    __table_args__ = (
        CheckConstraint("total_capacity > 0", name="chk_flight_capacity_positive"),
        UniqueConstraint("flight_number", "departure_time", name="uq_flight_number_departure"),
    )

class SeatInventory(Base):
    __tablename__ = "seat_inventory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    travel_class: Mapped[SeatClass] = mapped_column(SQLEnum(SeatClass), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    held_seats: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    base_price: Mapped[float] = mapped_column(nullable=False)

    flight: Mapped["Flight"] = relationship(back_populates="inventories")

    __table_args__ = (
        CheckConstraint("total_seats >= 0", name="chk_total_seats_non_negative"),
        CheckConstraint("available_seats >= 0", name="chk_available_seats_non_negative"),
        CheckConstraint("held_seats >= 0", name="chk_held_seats_non_negative"),
        CheckConstraint("base_price > 0", name="chk_base_price_positive"),
        UniqueConstraint("flight_id", "travel_class", name="uq_flight_seat_class"),
    )
