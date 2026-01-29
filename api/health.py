import asyncio
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Body, Request
from pydantic import BaseModel
import uvicorn

from config import settings
from models.models import Alert

logger = logging.getLogger(__name__)

# FastAPI App Definition
app = FastAPI(title="AlertOrchestrator Health", version="1.0.0")

# Import and include debug routes
from .debug_routes import trigger_router, debug_router
app.include_router(trigger_router)
app.include_router(debug_router)

@app.get("/health")
async def health_check(request: Request):
    """
    Kubernetes Liveness/Readiness Probe.
    """
    consumer = getattr(request.app.state, "consumer", None)
    
    if consumer:
        if consumer.is_connected:
            return {"status": "OK", "rabbitmq": "connected"}
        else:
            raise HTTPException(status_code=503, detail="RabbitMQ Disconnected")
            
    raise HTTPException(status_code=503, detail="Initializing")


async def start_health_server(consumer=None, orchestrator=None):
    """
    Start the FastAPI server via Uvicorn in a separate asyncio task.
    """
    # Store dependencies in app.state for access in routers
    app.state.consumer = consumer
    app.state.orchestrator = orchestrator
    
    config = uvicorn.Config(
        app=app, 
        host="0.0.0.0", 
        port=settings.HEALTH_PORT, 
        log_level="warning"
    )
    server = uvicorn.Server(config)
    
    # Run server in a task so it doesn't block the main loop
    task = asyncio.create_task(server.serve())
    
    # Return a wrapper object that matches the old interface (has cleanup method)
    class ServerHandle:
        async def cleanup(self):
            server.should_exit = True
            await task
            
    return ServerHandle()
