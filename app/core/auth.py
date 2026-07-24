from dataclasses import dataclass
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _decode_and_load_user(token: str, db: Session) -> tuple[User, Optional[int]]:
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    project_id = payload.get("project_id")
    return user, (int(project_id) if project_id is not None else None)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the calling user, and reject project-scoped tokens.

    Account-level actions (creating projects, minting project tokens) require
    a full login token, not a token that is already scoped to one project.
    """
    user, project_id = _decode_and_load_user(token, db)
    if project_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires a full account token, not a project token",
        )
    return user


@dataclass
class Actor:
    """The caller of a secrets or audit endpoint.

    project_id is None for a full account token, meaning the caller can act
    on any project they own. It is set for a project-scoped token, meaning
    the caller is restricted to that one project.
    """

    user: User
    project_id: Optional[int] = None


def get_current_actor(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Actor:
    user, project_id = _decode_and_load_user(token, db)
    return Actor(user=user, project_id=project_id)
