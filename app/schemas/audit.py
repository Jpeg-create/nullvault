from pydantic import BaseModel
from datetime import datetime


class AuditLogResponse(BaseModel):
    id: int
    action: str
    secret_name: str | None
    ip_address: str | None
    timestamp: datetime

    class Config:
        from_attributes = True
