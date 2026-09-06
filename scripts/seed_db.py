import asyncio
from datetime import datetime, timedelta, timezone
from app.core.database import Base, get_engine, get_session_factory
from app.schemas.flight import FlightCreate, SeatInventoryCreate
from app.models.flight import SeatClass
from app.services.inventory_service import InventoryService

async def seed():
    print("Seeding test flight data into Neon Postgres...")
    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with get_session_factory()() as session:
        dep_time = datetime.now(timezone.utc) + timedelta(days=2)
        arr_time = dep_time + timedelta(hours=7)

        sample_flight = FlightCreate(
            flight_number="EK501",
            origin="LHR",
            destination="DXB",
            departure_time=dep_time,
            arrival_time=arr_time,
            total_capacity=100,
            seat_allocations=[
                SeatInventoryCreate(travel_class=SeatClass.FIRST, total_seats=20, base_price=1200.0),
                SeatInventoryCreate(travel_class=SeatClass.BUSINESS, total_seats=30, base_price=650.0),
                SeatInventoryCreate(travel_class=SeatClass.ECONOMY, total_seats=50, base_price=250.0),
            ]
        )

        flight = await InventoryService.create_flight(session, sample_flight)
        print(f"[SUCCESS] Flight created: {flight.flight_number} (ID: {flight.id})")
        print(f"Route: {flight.origin} -> {flight.destination}")
        print("Seat allocations: 20 First, 30 Business, 50 Economy")

if __name__ == "__main__":
    asyncio.run(seed())
