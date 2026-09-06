import uuid
import httpx
from langchain_core.tools import tool
from pinecone import Pinecone
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

API_BASE = "http://127.0.0.1:8000/api/v1"

def is_valid_uuid(val: str) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

@tool
def search_flights_tool(origin: str, destination: str) -> str:
    """Search for scheduled flights between airport codes (e.g. LHR to DXB). Returns flight UUIDs and seat availability."""
    with httpx.Client() as client:
        res = client.get(f"{API_BASE}/flights/search", params={"origin": origin.upper(), "destination": destination.upper()})
        if res.status_code != 200 or not res.json():
            return f"No scheduled flights found from {origin} to {destination}."
        
        flights = res.json()
        summary = []
        for f in flights:
            invs = ", ".join([f"{i['travel_class']}: {i['available_seats']} available at ${i['base_price']}" for i in f['inventories']])
            summary.append(f"Flight Number: {f['flight_number']} | DB_UUID: {f['id']} | Departs: {f['departure_time']} | Seats: [{invs}]")
        return "\n".join(summary)

@tool
def hold_seat_tool(flight_id_or_number: str, passenger_name: str, passenger_email: str, travel_class: str, fare_type: str) -> str:
    """Puts a temporary atomic hold on a seat.
    flight_id_or_number can be either the flight database UUID or the flight number (e.g. 'EK501').
    travel_class must be ECONOMY, BUSINESS, or FIRST.
    fare_type must be BASIC_ECONOMY, FLEXIBLE, or REFUNDABLE.
    """
    resolved_flight_id = flight_id_or_number

    # If user/LLM passed a flight code like EK501 instead of UUID, find its UUID
    if not is_valid_uuid(flight_id_or_number):
        with httpx.Client() as client:
            # Common route check or query search endpoint
            res = client.get(f"{API_BASE}/flights/search", params={"origin": "LHR", "destination": "DXB"})
            if res.status_code == 200:
                matches = [f for f in res.json() if f["flight_number"].upper() == flight_id_or_number.upper()]
                if matches:
                    resolved_flight_id = matches[0]["id"]
                else:
                    return f"Error: Could not find a flight matching number '{flight_id_or_number}'."
            else:
                return f"Error: Could not resolve flight number '{flight_id_or_number}'."

    payload = {
        "flight_id": resolved_flight_id,
        "passenger_name": passenger_name,
        "passenger_email": passenger_email,
        "travel_class": travel_class.upper(),
        "fare_type": fare_type.upper(),
        "hold_duration_minutes": 10
    }
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    
    with httpx.Client() as client:
        res = client.post(f"{API_BASE}/bookings/hold", json=payload, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return f"SUCCESS: Hold placed! Booking ID: {data['booking_id']}. Total: ${data['total_price']}. Expires: {data['hold_expires_at']}."
        return f"FAILED ({res.status_code}): {res.text}"

@tool
def confirm_booking_tool(booking_id: str) -> str:
    """Confirms a held booking after payment."""
    with httpx.Client() as client:
        res = client.post(f"{API_BASE}/bookings/confirm", json={"booking_id": booking_id, "payment_reference": "CARD-MOCK-999"})
        if res.status_code == 200:
            return f"SUCCESS: Booking {booking_id} is permanently CONFIRMED."
        return f"FAILED ({res.status_code}): {res.text}"

@tool
def cancel_booking_tool(booking_id: str) -> str:
    """Cancels a booking and computes refunds or travel credits according to fare rules."""
    with httpx.Client() as client:
        res = client.post(f"{API_BASE}/bookings/cancel", json={"booking_id": booking_id, "reason": "Terminal request"})
        if res.status_code == 200:
            data = res.json()
            return f"CANCELLED: Status: {data['status']}. Cash Refund: ${data['refund_amount']}. Travel Credit: ${data['travel_credit']}."
        return f"FAILED ({res.status_code}): {res.text}"

@tool
def policy_rag_tool(query: str) -> str:
    """Search airline fare rules, refund terms, and delay compensation guidelines."""
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=settings.GEMINI_API_KEY,
        output_dimensionality=768,
        task_type="RETRIEVAL_QUERY",
    )
    vector = embeddings.embed_query(query)
    results = index.query(vector=vector, top_k=2, include_metadata=True)
    matches = [m["metadata"]["text"] for m in results["matches"]]
    return "\n\n".join(matches) if matches else "No relevant policy documents found."
