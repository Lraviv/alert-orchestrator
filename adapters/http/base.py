import httpx
import logging
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class BaseHTTPClient:
    """
    Base generic HTTP client handling common logic like:
    - Retry policies
    - SSL verification configuration
    - Error logging
    """
    def __init__(self, base_url: str, timeout: float, verify_ssl: bool = True):
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def _post(self, endpoint: str, json_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Internal helper for making POST requests with retries.
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
            try:
                response = await client.post(url, json=json_payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Error {e.response.status_code} calling {url}: {e}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Connection Error calling {url}: {e}")
                raise
