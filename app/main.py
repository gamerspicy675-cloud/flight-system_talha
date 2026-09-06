from fastapi import FastAPI
from app.api.v1.flights import router as flights_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(flights_router, prefix=settings.API_V1_STR, tags=["Flights & Bookings"])

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME}