from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


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
    fingerprint: Optional[str] = None

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
    email: str
    group_name: Optional[str] = None
    priority: str = "normal"
