from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_actor, Actor
from app.models.audit import AuditLog
from app.models.project import Project
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/", response_model=List[AuditLogResponse])
def get_audit_logs(
    project: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    query = db.query(AuditLog).filter(AuditLog.user_id == actor.user.id)

    if actor.project_id is not None:
        scoped_project = db.query(Project).filter(Project.id == actor.project_id).first()
        if not scoped_project:
            raise HTTPException(status_code=404, detail="Project not found")
        query = query.filter(AuditLog.project_name == scoped_project.name)
    elif project is not None:
        name = project.strip().lower()
        if not db.query(Project).filter(Project.user_id == actor.user.id, Project.name == name).first():
            raise HTTPException(status_code=404, detail="Project not found")
        query = query.filter(AuditLog.project_name == name)

    return query.order_by(AuditLog.timestamp.desc()).all()
