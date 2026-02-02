import logging
import sys
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Environment
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    USE_MOCKS: bool = False
    HEALTH_PORT: int = 8081
    SSL_VERIFY: bool = True

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_QUEUE_NAME: str = "alerts"
    RABBITMQ_PREFETCH_COUNT: int = 50

    # Project Manager API
    PROJECT_MANAGER_API_URL: str = "http://project-manager:8080"
    PROJECT_MANAGER_API_TIMEOUT: float = 10.0

    # Alert DB API
    ALERT_DB_API_URL: str = "http://alert-db:8080"
    ALERT_DB_API_TIMEOUT: float = 10.0

    # SMTP
    SMTP_HOSTNAME: str = "smtp.example.com"
    SMTP_PORT: int = 25
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = False
    SMTP_TIMEOUT: float = 10.0
    SMTP_POOL_SIZE: int = 20
    EMAIL_FROM: str = "alerts@example.com"


settings = Settings()


def setup_logging():
    if settings.ENVIRONMENT == "production":
        from pythonjsonlogger import jsonlogger
        
        logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(settings.LOG_LEVEL)
    else:
        logging.basicConfig(
            level=settings.LOG_LEVEL,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )
