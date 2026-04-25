from pydantic import BaseModel
from datetime import datetime


class SecretCreate(BaseModel):
    name: str
    value: str


class SecretResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
