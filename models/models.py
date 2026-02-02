from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

class AlertStatus(str, Enum):
    OK = "ok"
    DEDUP = "dedup"

class Alert(BaseModel):
    """
    Alert schema compatible with Alertmanager webhook payload.
    """
    status: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: datetime
    endsAt: Optional[datetime] = None
    generatorURL: Optional[str] = None
    dedup_key: str = Field(..., alias="fingerprint")
    
    model_config = {"populate_by_name": True}

    @property
    def vendor(self) -> Optional[str]:
        return self.labels.get("vendor")

    @property
    def environment(self) -> Optional[str]:
        return self.labels.get("environment")

    @property
    def site(self) -> Optional[str]:
        return self.labels.get("site")

    @property
    def severity(self) -> str:
        return self.labels.get("severity", "info")


class Recipient(BaseModel):
    """
    Recipient information resolved from Project Manager.
    """
    project_id: str
    project_name: str
    alert_groups: list[str] = Field(default_factory=list)
    # alert_groups contains the list of email addresses to notify 
    
class FullAlert(Alert, Recipient):
    """
    Combines Alert and Recipient data into a single context.
    """
    pass
