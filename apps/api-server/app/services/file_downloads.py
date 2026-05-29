from __future__ import annotations

from pathlib import Path
from re import sub

from fastapi import HTTPException, Request, status
from fastapi.responses import FileResponse
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ALGORITHM
from app.db.models import AuditLog, DownloadResource, FileRecord, User
from app.services.request_context import extract_request_meta


DOWNLOAD_ACTION_SUCCESS = "file_download_success"
DOWNLOAD_ACTION_DENIED = "file_download_denied"
DOWNLOAD_ACTION_NOT_FOUND = "file_download_not_found"
DOWNLOAD_ACTION_PATH_INVALID = "file_download_path_invalid"


def safe_download_filename(origin_name: str | None) -> str:
    name = (origin_name or "download").strip()
    name = name.replace("\\", "_").replace("/", "_").replace("\r", "_").replace("\n", "_")
    name = sub(r"[\x00-\x1f\x7f]+", "_", name)
    name = sub(r"\s+", " ", name).strip(" .")
    return name[:180] or "download"


def resolve_file_path(file_record: FileRecord) -> Path:
    storage_root = Path(settings.storage_root).resolve()
    raw_path = Path(file_record.storage_path)
    candidate = raw_path if raw_path.is_absolute() else storage_root / raw_path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(storage_root)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File path is not allowed") from None
    if not resolved.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return resolved


def build_download_response(file_record: FileRecord, resolved_path: Path) -> FileResponse:
    media_type = file_record.mime_type or "application/octet-stream"
    return FileResponse(
        path=resolved_path,
        media_type=media_type,
        filename=safe_download_filename(file_record.origin_name),
    )


def audit_file_download(
    db: Session,
    *,
    request: Request,
    action: str,
    result: str,
    resource_id: int | None,
    file_record: FileRecord | None = None,
    user: User | None = None,
    actor_type: str = "anonymous",
    reason: str | None = None,
    is_public: bool | None = None,
) -> None:
    meta = extract_request_meta(request)
    detail = {
        "actor_type": actor_type,
        "resource_id": resource_id,
        "file_id": file_record.id if file_record else None,
        "origin_name": file_record.origin_name if file_record else None,
        "is_public": is_public,
        "username": user.username if user else None,
        "result": result,
        "reason": reason,
    }
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            module="downloads",
            action=action,
            object_type="download_resource",
            object_id=str(resource_id) if resource_id is not None else None,
            detail_json=detail,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
            path=meta.path,
            method=meta.method,
            result=result,
            failure_reason=reason,
        )
    )


def resolve_active_user_from_request(db: Session, request: Request) -> tuple[User | None, str | None]:
    auth_header = request.headers.get("authorization") or ""
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None, "missing_credentials"
    try:
        payload = jwt.decode(token.strip(), settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            return None, "missing_subject"
        user_id = int(subject)
    except ExpiredSignatureError:
        return None, "token_expired"
    except (JWTError, ValueError):
        return None, "invalid_token"
    user = db.get(User, user_id)
    if not user or user.status != "active":
        return None, "inactive_or_missing_user"
    return user, None


def serialize_file_record(file_record: FileRecord) -> dict:
    return {
        "id": file_record.id,
        "origin_name": file_record.origin_name,
        "mime_type": file_record.mime_type,
        "size": file_record.size,
        "owner_id": file_record.owner_id,
        "created_at": file_record.created_at,
        "updated_at": file_record.updated_at,
    }


def serialize_download_resource(resource: DownloadResource, *, file_record: FileRecord | None = None) -> dict:
    file_data = serialize_file_record(file_record) if file_record else None
    public_download_url = f"{settings.api_prefix}/public/downloads/{resource.id}/download" if resource.is_public else None
    return {
        "id": resource.id,
        "title": resource.title,
        "slug": resource.slug,
        "summary": resource.summary,
        "category_id": resource.category_id,
        "file_id": resource.file_id,
        "file": file_data,
        "is_public": resource.is_public,
        "download_count": resource.download_count,
        "sort_order": resource.sort_order,
        "download_url": public_download_url or f"{settings.api_prefix}/downloads/{resource.id}/download",
        "public_download_url": public_download_url,
        "protected_download_url": f"{settings.api_prefix}/downloads/{resource.id}/download",
        "created_at": resource.created_at,
        "updated_at": resource.updated_at,
    }
