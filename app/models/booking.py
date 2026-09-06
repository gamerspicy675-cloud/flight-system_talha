import uuid
from datetime import datetime
import enum
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Numeric, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.flight import SeatClass

if TYPE_CHECKING:
    from app.models.flight import Flight

class BookingStatus(str, enum.Enum):
    HELD = "HELD"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"

class FareType(str, enum.Enum):
    BASIC_ECONOMY = "BASIC_ECONOMY"
    FLEXIBLE = "FLEXIBLE"
    REFUNDABLE = "REFUNDABLE"

class WaitlistStatus(str, enum.Enum):
    PENDING = "PENDING"
    NOTIFIED = "NOTIFIED"
    CLAIMED = "CLAIMED"
    EXPIRED = "EXPIRED"

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("flights.id"), nullable=False)
    passenger_name: Mapped[str] = mapped_column(String(255), nullable=False)
    passenger_email: Mapped[str] = mapped_column(String(255), nullable=False)
    travel_class: Mapped[SeatClass] = mapped_column(SQLEnum(SeatClass), nullable=False)
    fare_type: Mapped[FareType] = mapped_column(SQLEnum(FareType), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(SQLEnum(BookingStatus), default=BookingStatus.HELD, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    flight: Mapped["Flight"] = relationship(back_populates="bookings")

class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flight_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("flights.id", ondelete="CASCADE"), nullable=False)
    passenger_name: Mapped[str] = mapped_column(String(255), nullable=False)
    passenger_email: Mapped[str] = mapped_column(String(255), nullable=False)
    travel_class: Mapped[SeatClass] = mapped_column(SQLEnum(SeatClass), nullable=False)
    loyalty_tier: Mapped[str] = mapped_column(String(20), default="STANDARD")
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[WaitlistStatus] = mapped_column(SQLEnum(WaitlistStatus), default=WaitlistStatus.PENDING, nullable=False)
    notified_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    flight: Mapped["Flight"] = relationship(back_populates="waitlist_entries")
