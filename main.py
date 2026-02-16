import asyncio
import signal
import sys
import logging

from config import setup_logging
from dependencies import create_top_level_dependencies
from api.health import start_health_server

logger = logging.getLogger(__name__)


async def main():
    setup_logging()
    logger.info("Service starting...")

    consumer = None
    orchestrator = None
    health_runner = None

    # Wire up dependencies
    try:
        consumer, orchestrator = create_top_level_dependencies()
    except Exception as e:
        logger.error(f"Failed to initialize dependencies: {e}")
        sys.exit(1)

    # Start Healthcheck Server
    try:
        health_runner = await start_health_server(consumer=consumer, orchestrator=orchestrator)
    except Exception as e:
        logger.error(f"Failed to start healthcheck server: {e}")
        sys.exit(1)

    # Signal Handling
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    async def signal_handler():
        logger.info("Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(signal_handler()))
        except NotImplementedError:
            # Windows ProactorEventLoop does not support add_signal_handler
            logger.warning(f"Signal {sig} handling not supported on this platform/loop.")

    try:
        # Start Adapters
        if orchestrator:
             await orchestrator.startup()
             
        # Connect Consumer
        if consumer:
            await consumer.connect()
        logger.info("Service ready")
        
        await stop_event.wait()
    except Exception as e:
        logger.error(f"Service runtime error: {e}")
        sys.exit(1)
    finally:
        logger.info("Service stopping")
        if consumer:
            await consumer.close()
        if orchestrator:
            await orchestrator.shutdown()
        logger.info("Cleaning up healthcheck server...")
        if health_runner:
            await health_runner.cleanup()
        logger.info("Service stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
