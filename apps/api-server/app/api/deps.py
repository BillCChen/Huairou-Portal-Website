from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.models import User
from app.db.session import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login/password")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
    except (JWTError, ValueError):
        raise credentials_exception from None

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or user.status != "active":
        raise credentials_exception
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.code not in {"super_admin", "content_admin", "auditor"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return user


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role.code != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
    return user
