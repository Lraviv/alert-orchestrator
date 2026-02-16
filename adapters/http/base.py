import httpx
import logging
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception

logger = logging.getLogger(__name__)


def _should_retry(e: BaseException) -> bool:
    """
    Retry on:
    - Connection Errors (httpx.RequestError)
    - Server Errors (5xx)
    - Rate Limits (429)
    - Request Timeouts (408)
    """
    if isinstance(e, httpx.RequestError):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        return code >= 500 or code == 429 or code == 408
    return False

# Reusable Retry Policy
http_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_should_retry),
)

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
        self.client: Optional[httpx.AsyncClient] = None

    def _build_url(self, endpoint: str) -> str:
        """Construct full URL."""
        return f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
    async def start(self):
        """
        Initialize the persistent HTTP client.
        httpx.AsyncClient manages a connection pool automatically.
        """
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl)

    async def close(self):
        """Close the persistent HTTP client."""
        if self.client:
            await self.client.aclose()

    @http_retry
    async def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """
        Generic internal helper for making HTTP requests with retries and error logging.
        Returns the raw httpx.Response object.
        """
        url = self._build_url(endpoint)
        
        await self.start()
            
        try:
            if method.lower() == "post":
                response = await self.client.post(url, **kwargs)
            elif method.lower() == "get":
                response = await self.client.get(url, **kwargs)
            elif method.lower() == "patch":
                response = await self.client.patch(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                logger.warning(f"Server Error {e.response.status_code} calling {url}: {e}. Retrying...")
            else:
                logger.error(f"Client Error {e.response.status_code} calling {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.warning(f"Connection Error calling {url}: {e}. Retrying...")
            raise

    async def _post(self, endpoint: str, json_payload: dict[str, Any]) -> httpx.Response:
        """
        Internal helper for making POST requests.
        """
        return await self._request("post", endpoint, json=json_payload)
    
    async def _patch(self, endpoint: str, json_payload: dict[str, Any]) -> httpx.Response:
        """
        Internal helper for making PATCH requests.
        """
        return await self._request("patch", endpoint, json=json_payload)

    async def _get(self, endpoint: str, params: dict[str, Any] = None) -> httpx.Response:
        """
        Internal helper for making GET requests.
        """
        return await self._request("get", endpoint, params=params)
