from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.services.request_context import current_request_meta


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login/password")


def record_unauthorized_access(db: Session, reason: str) -> None:
    meta = current_request_meta()
    try:
        db.add(
            AuditLog(
                user_id=None,
                module="auth",
                action="unauthorized",
                object_type="protected_route",
                object_id=None,
                detail_json={"reason": reason},
                ip_address=meta.ip_address,
                user_agent=meta.user_agent,
                path=meta.path,
                method=meta.method,
                result="failure",
                failure_reason=reason,
            )
        )
        db.commit()
    except Exception:
        db.rollback()


def get_current_user(_request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            record_unauthorized_access(db, "missing_subject")
            raise credentials_exception
        user_id = int(subject)
    except ExpiredSignatureError:
        record_unauthorized_access(db, "token_expired")
        raise credentials_exception from None
    except (JWTError, ValueError):
        record_unauthorized_access(db, "invalid_token")
        raise credentials_exception from None

    user = db.scalar(select(User).where(User.id == user_id))
    if not user or user.status != "active":
        record_unauthorized_access(db, "inactive_or_missing_user")
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
