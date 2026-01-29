from fastapi import APIRouter, HTTPException, Request
from models.models import Alert
import logging

logger = logging.getLogger(__name__)

trigger_router = APIRouter()
debug_router = APIRouter(prefix="/debug", tags=["Debug"])

@trigger_router.post("/trigger")
async def trigger_alert(alert: Alert, request: Request):
    """
    Manually trigger an alert in DEV mode (stubs).
    """
    # Access consumer from app state
    consumer = getattr(request.app.state, "consumer", None)
    
    if not consumer:
        raise HTTPException(status_code=503, detail="Consumer not initialized")
        
    # Check if consumer is a stub with simulate_alert
    if not hasattr(consumer, 'simulate_alert'):
        raise HTTPException(status_code=501, detail="Trigger not available (Not using mocks)")
    
    try:
        await consumer.simulate_alert(alert.model_dump())
        return {"message": "Alert triggered successfully", "fingerprint": alert.dedup_key}
    except Exception as e:
        logger.error(f"Trigger failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@debug_router.post("/process")
async def debug_process_alert(alert: Alert, request: Request):
    """
    Production Debug: Directly invoke the orchestrator to process an alert.
    WARNING: This will send REAL emails/notifications if configured.
    """
    # Access orchestrator from app state
    orchestrator = getattr(request.app.state, "orchestrator", None)

    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        
    try:
        logger.warning(f"Manual debug processing triggered for {alert.dedup_key}")
        await orchestrator.process_alert(alert)
        return {"message": "Alert processed successfully", "fingerprint": alert.dedup_key}
    except Exception as e:
        logger.error(f"Debug process failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
