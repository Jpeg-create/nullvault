from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.security import create_access_token
from app.core.config import settings
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse
from app.schemas.user import Token

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = project.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")
    if db.query(Project).filter(Project.user_id == current_user.id, Project.name == name).first():
        raise HTTPException(status_code=400, detail="Project with this name already exists")
    new_project = Project(user_id=current_user.id, name=name)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@router.get("/", response_model=List[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Project).filter(Project.user_id == current_user.id).all()


@router.post("/{name}/token", response_model=Token)
def create_project_token(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.user_id == current_user.id, Project.name == name.strip().lower())
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    token = create_access_token(
        {"sub": str(current_user.id), "project_id": str(project.id)},
        expire_minutes=settings.project_token_expire_minutes,
    )
    return {"access_token": token, "token_type": "bearer"}
