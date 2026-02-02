import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from adapters.email.pool import SMTPConnectionPool
from config import settings

@pytest.mark.asyncio
async def test_smtp_connection_pool():
    # Setup
    # Force pool size to 2 for minimal testing
    settings.SMTP_POOL_SIZE = 2
    pool = SMTPConnectionPool()
    
    # Mock SMTP Client
    mock_smtp = AsyncMock()
    mock_smtp.connect = AsyncMock()
    mock_smtp.is_connected = True
    
    with patch("adapters.email.pool.aiosmtplib.SMTP", return_value=mock_smtp):
        # 1. Connect (fill pool)
        await pool.connect()
        assert pool.pool.qsize() == 2
        
        # 2. Acquire connection
        async with pool.acquire() as conn1:
             assert conn1 is mock_smtp
             assert pool.pool.qsize() == 1
             
             # Acquire second
             async with pool.acquire() as conn2:
                 assert conn2 is mock_smtp
                 assert pool.pool.qsize() == 0
        
        # 3. Released back
        assert pool.pool.qsize() == 2
        
        # 4. Close
        await pool.close()
        assert pool.pool.empty()
