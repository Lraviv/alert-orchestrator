from datetime import datetime
from models.models import Alert, Recipient

def create_alert(
    status: str = "firing",
    alertname: str = "TestAlert",
    severity: str = "critical",
    description: str = "Something failed",
    dedup_key: str = "test-fp",
    vendor: str = "TestVendor",
    starts_at: datetime = None
) -> Alert:
    """
    Factory function to create an Alert object with default test values.
    """
    if starts_at is None:
        starts_at = datetime.now()
        
    return Alert(
        status=status,
        labels={
            "alertname": alertname,
            "severity": severity,
            "vendor": vendor,
            "site": "TestSite",
            "environment": "TestEnv"
        },
        annotations={
            "description": description
        },
        startsAt=starts_at,
        dedup_key=dedup_key,
        generatorURL="http://prometheus/graph"
    )

def create_recipient(email: str = "test@example.com", project_name: str = "TestProject") -> Recipient:
    """
    Factory function to create a Recipient object.
    """
    return Recipient(
        email=email, 
        project_name=project_name, 
        project_id="prj-123", 
        alert_groups=["DevOps"]
    )

def create_alert_payload(**overrides) -> dict:
    """
    Factory function to create a raw dict payload (e.g. from Alertmanager webhook).
    """
    defaults = {
        "status": "firing",
        "labels": {
            "alertname": "TestAlert",
            "severity": "critical",
            "site": "New York"
        },
        "annotations": {
            "description": "Memory usage exceeded 90%"
        },
        "startsAt": "2024-01-01T12:00:00Z",
        "fingerprint": "test-fingerprint",
        "generatorURL": "http://prometheus:9090"
    }
    defaults.update(overrides)
    return defaults
