from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_actor, Actor
from app.models.project import Project
from app.models.secret import Secret
from app.models.audit import AuditLog
from app.schemas.secret import SecretCreate, SecretResponse
from cryptography.fernet import Fernet
import os

router = APIRouter(prefix="/secrets", tags=["Secrets"])

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
fernet = Fernet(ENCRYPTION_KEY)


def log_action(db, user_id, project_name, action, secret_name=None, ip=None):
    db.add(
        AuditLog(
            user_id=user_id,
            project_name=project_name,
            action=action,
            secret_name=secret_name,
            ip_address=ip,
        )
    )
    db.commit()


def resolve_project(db: Session, actor: Actor, project_name: str) -> Project:
    """Look up a project by name, scoped to the actor's account.

    If the actor is carrying a project-scoped token, the resolved project
    must match the project baked into that token. This is what stops a
    project token from reaching into a different project owned by the
    same account.
    """
    name = project_name.strip().lower()
    project = db.query(Project).filter(Project.user_id == actor.user.id, Project.name == name).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if actor.project_id is not None and actor.project_id != project.id:
        raise HTTPException(status_code=403, detail="This token is not authorized for that project")
    return project


def to_response(secret: Secret, project: Project) -> SecretResponse:
    return SecretResponse(
        id=secret.id,
        project=project.name,
        name=secret.name,
        created_at=secret.created_at,
        updated_at=secret.updated_at,
    )


@router.post("/", response_model=SecretResponse, status_code=201)
def create_secret(
    secret: SecretCreate,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    project = resolve_project(db, actor, secret.project)
    if db.query(Secret).filter(Secret.project_id == project.id, Secret.name == secret.name).first():
        raise HTTPException(status_code=400, detail="Secret with this name already exists in this project")
    encrypted = fernet.encrypt(secret.value.encode()).decode()
    new_secret = Secret(project_id=project.id, name=secret.name, encrypted_value=encrypted)
    db.add(new_secret)
    db.commit()
    db.refresh(new_secret)
    log_action(db, actor.user.id, project.name, "CREATE", secret.name)
    return to_response(new_secret, project)


@router.get("/", response_model=List[SecretResponse])
def list_secrets(
    project: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    query = db.query(Secret).join(Project).filter(Project.user_id == actor.user.id)

    if actor.project_id is not None:
        query = query.filter(Project.id == actor.project_id)
    elif project is not None:
        resolved = resolve_project(db, actor, project)
        query = query.filter(Project.id == resolved.id)

    secrets = query.all()
    return [to_response(s, s.project) for s in secrets]


@router.get("/{project}/{name}")
def get_secret(
    project: str,
    name: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    proj = resolve_project(db, actor, project)
    secret = db.query(Secret).filter(Secret.project_id == proj.id, Secret.name == name).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    decrypted = fernet.decrypt(secret.encrypted_value.encode()).decode()
    log_action(db, actor.user.id, proj.name, "READ", name)
    return {"project": proj.name, "name": secret.name, "value": decrypted}


@router.delete("/{project}/{name}", status_code=204)
def delete_secret(
    project: str,
    name: str,
    db: Session = Depends(get_db),
    actor: Actor = Depends(get_current_actor),
):
    proj = resolve_project(db, actor, project)
    secret = db.query(Secret).filter(Secret.project_id == proj.id, Secret.name == name).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    db.delete(secret)
    db.commit()
    log_action(db, actor.user.id, proj.name, "DELETE", name)
