from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    secret_name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
