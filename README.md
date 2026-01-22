# AlertOrchestrator

Reliable, asynchronous, event-driven microservice for delivering alert notifications in an offline OpenShift environment.

## Features

- **Asynchronous Processing**: Built with `asyncio`, `aio-pika`, and `httpx`.
- **Reliable Delivery**: Retries, deduplication (via AlertDB), and persistence.
- **Recipient Resolution**: Dynamic lookup via Project Manager API.
- **HTML Emails**: Professional Jinja2-based email templates.
- **Smart Healthcheck**: Readiness probe verifies RabbitMQ connection status.
- **Observability**: Structured JSON logging for production.
- **Developer Friendly**: Local mocks and `uv` based dependency management.

## Setup

This project uses `uv` for fast dependency management.

1. **Install uv** (if not installed):
   ```bash
   pip install uv
   ```

2. **Install Dependencies**:
   ```bash
   uv sync
   # OR
   pip install .
   ```

3. **Run Locally (with Mocks)**:
   You can run the service without any external dependencies using Mocks.
   ```powershell
   $env:USE_MOCKS="True"
   python main.py
   ```
   *The service will start on port 8081 (Healthcheck) and log to console.*

## Configuration

Configuration is managed via environment variables (see `config.py`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `production` | Set to `production` for JSON logs |
| `LOG_LEVEL` | `INFO` | Logging level |
| `USE_MOCKS` | `False` | Enable local in-memory mocks |
| `HEALTH_PORT` | `8081` | Port for `/health` endpoint |
| `SSL_VERIFY` | `True` | Verify SSL certificates for internal APIs |
| `RABBITMQ_URL` | `...` | AMQP Connection URL |
| `PROJECT_MANAGER_API_URL` | `...` | Recipient Resolution API |
| `ALERT_DB_API_URL` | `...` | Persistence/Dedup API |
| `SMTP_HOSTNAME` | `...` | SMTP Relay Host |

## Testing

Run unit tests using `pytest` (via `uv`):

```bash
uv run pytest
```

## Deployment

A `Dockerfile` is provided using the efficient `uv` setup:

```bash
docker build -t alert-orchestrator .
docker run -p 8081:8081 alert-orchestrator
```

## Healthcheck

The service exposes a readiness probe at `GET /health`.
- **200 OK**: Service is ready and connected to RabbitMQ.
- **503 Service Unavailable**: Service is disconnected or initializing.
