import logging
import asyncio
import aiosmtplib
from typing import Optional
from contextlib import asynccontextmanager

from config import settings

logger = logging.getLogger(__name__)


class SMTPConnectionPool:
    """
    Manages a pool of SMTP connections.
    """
    def __init__(self):
        self.hostname = settings.SMTP_HOSTNAME
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_USE_TLS
        self.timeout = settings.SMTP_TIMEOUT
        self.pool_size = settings.SMTP_POOL_SIZE
        
        self.pool: asyncio.Queue[aiosmtplib.SMTP] = asyncio.Queue()
        self._pool_created = False

    async def _create_connection(self) -> aiosmtplib.SMTP:
        """Helper to create and connect a new SMTP client."""
        client = aiosmtplib.SMTP(
            hostname=self.hostname,
            port=self.port,
            use_tls=self.use_tls,
            timeout=self.timeout
        )
        await client.connect()
        if self.username and self.password:
            await client.login(self.username, self.password)
        return client

    async def connect(self):
        """Initialize the SMTP connection pool."""
        if self._pool_created:
            return

        logger.info(f"Creating SMTP connection pool with {self.pool_size} connections...")
        for _ in range(self.pool_size):
            try:
                client = await self._create_connection()
                await self.pool.put(client)
            except Exception as e:
                logger.error(f"Failed to create initial SMTP connection: {e}")
                # We continue, assuming we might retry later or operate with fewer connections
                pass
        
        self._pool_created = True

    async def close(self):
        """Close all connections in the pool."""
        logger.info("Closing SMTP connection pool...")
        while not self.pool.empty():
            try:
                client = self.pool.get_nowait()
                client.close()
            except Exception as e:
                logger.error(f"Error closing SMTP connection: {e}")

    @asynccontextmanager
    async def acquire(self):
        """
        Context manager to acquire a connection from the pool.
        Handles reconnection if the acquired connection is closed.
        """
        # Ensure pool is initialized (lazy init safety)
        if not self._pool_created:
            await self.connect()

        client = await self.pool.get()
        try:
            # Check health / Reconnect if needed
            if not client.is_connected:
                try:
                    logger.info("Reconnect SMTP client...")
                    client.close() # Clean up old one
                    client = await self._create_connection()
                except Exception as e:
                    logger.error(f"Failed to reconnect SMTP client: {e}")
                    raise e
            
            yield client
        finally:
            # Always return client to pool
            await self.pool.put(client)
