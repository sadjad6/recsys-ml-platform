"""
Event Service API Routes.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from .schemas import EventPayload, EventEnriched, EventResponse
from .producer import producer

router = APIRouter()

@router.post("/", response_model=EventResponse, status_code=202)
async def ingest_event(event: EventPayload, background_tasks: BackgroundTasks):
    """
    Ingest a user interaction event.
    Returns 202 Accepted immediately and processes Kafka publish in background.
    """
    # Enrich the event with UUID and timestamp
    enriched_event = EventEnriched(**event.model_dump())
    
    try:
        # Publish to Kafka
        # Note: We await it directly here to ensure delivery, but in high-throughput 
        # scenarios, it could be pushed to a BackgroundTask. 
        # Since producer handles batching, await is usually fine.
        await producer.publish_event(enriched_event.model_dump())
        
        return EventResponse(
            status="accepted",
            event_id=enriched_event.event_id
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail="Failed to publish event to message queue.")
