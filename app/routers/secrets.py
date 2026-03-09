from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.secret import Secret
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.secret import SecretCreate, SecretResponse
from cryptography.fernet import Fernet
import os

router = APIRouter(prefix="/secrets", tags=["Secrets"])

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
fernet = Fernet(ENCRYPTION_KEY)


def log_action(db, user_id, action, secret_name=None, ip=None):
    db.add(AuditLog(user_id=user_id, action=action, secret_name=secret_name, ip_address=ip))
    db.commit()


@router.post("/", response_model=SecretResponse, status_code=201)
def create_secret(
    secret: SecretCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Secret).filter(Secret.user_id == current_user.id, Secret.name == secret.name).first():
        raise HTTPException(status_code=400, detail="Secret with this name already exists")
    encrypted = fernet.encrypt(secret.value.encode()).decode()
    new_secret = Secret(user_id=current_user.id, name=secret.name, encrypted_value=encrypted)
    db.add(new_secret)
    db.commit()
    db.refresh(new_secret)
    log_action(db, current_user.id, "CREATE", secret.name)
    return new_secret


@router.get("/", response_model=List[SecretResponse])
def list_secrets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Secret).filter(Secret.user_id == current_user.id).all()


@router.get("/{name}")
def get_secret(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    secret = db.query(Secret).filter(Secret.user_id == current_user.id, Secret.name == name).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    decrypted = fernet.decrypt(secret.encrypted_value.encode()).decode()
    log_action(db, current_user.id, "READ", name)
    return {"name": secret.name, "value": decrypted}


@router.delete("/{name}", status_code=204)
def delete_secret(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    secret = db.query(Secret).filter(Secret.user_id == current_user.id, Secret.name == name).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    db.delete(secret)
    db.commit()
    log_action(db, current_user.id, "DELETE", name)
