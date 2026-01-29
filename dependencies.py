from typing import Union, Tuple
import logging

from config import settings
from adapters.email.factory import EmailSenderFactory
from adapters.http.alert_db import AlertDBClient
from adapters.http.project_manager import ProjectManagerClient
from adapters.messaging.rabbitmq import RabbitMQConsumer
from adapters.stubs import (
    AlertDBClientStub,
    ProjectManagerClientStub,
    EmailSenderStub,
    RabbitMQConsumerStub,
)
from services.orchestrator import AlertOrchestrator

logger = logging.getLogger(__name__)


def create_top_level_dependencies() -> Tuple[Union[RabbitMQConsumer, RabbitMQConsumerStub], AlertOrchestrator]:
    """
    Wire up and return the RabbitMQConsumer and Orchestrator.
    """
    logger.info("Initializing dependencies...")

    if settings.USE_MOCKS:
        logger.warning("Using MOCK adapters!")
        alert_db = AlertDBClientStub()
        project_manager = ProjectManagerClientStub()
        email_sender = EmailSenderStub()
        
        orchestrator = AlertOrchestrator(
            alert_db_client=alert_db,
            project_manager_client=project_manager,
            email_sender=email_sender,
        )
        # Note: Stub consumer doesn't really consume unless extended to poll a file or something.
        consumer = RabbitMQConsumerStub(process_alert_callback=orchestrator.process_alert)
    else:
        alert_db = AlertDBClient()
        project_manager = ProjectManagerClient()
        email_sender = EmailSenderFactory.create(settings)

        orchestrator = AlertOrchestrator(
            alert_db_client=alert_db,
            project_manager_client=project_manager,
            email_sender=email_sender,
        )

        consumer = RabbitMQConsumer(process_alert_callback=orchestrator.process_alert)
    
    logger.info("Dependencies initialized.")
    return consumer, orchestrator
