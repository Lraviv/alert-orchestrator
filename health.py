import asyncio
import logging
from aiohttp import web

from config import settings

logger = logging.getLogger(__name__)


async def health_handler(request):
    consumer = request.app.get("consumer")
    if consumer:
        if consumer.is_connected:
            return web.Response(text="OK", status=200)
        else:
            return web.Response(text="RabbitMQ Disconnected", status=503)
            
    # If no consumer attached (e.g. startup?), assume OK or Initializing?
    # Better to prevent "ready" if not connected.
    return web.Response(text="Initializing", status=503)


async def start_health_server(consumer=None):
    app = web.Application()
    app["consumer"] = consumer
    app.router.add_get("/health", health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", settings.HEALTH_PORT)
    
    logger.info(f"Starting healthcheck server on port {settings.HEALTH_PORT}")
    await site.start()
    
    return runner
