from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_super_admin
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import (
    Article,
    ArticleTag,
    AuditLog,
    Banner,
    CaseStudy,
    CaseTag,
    Category,
    DownloadResource,
    FileRecord,
    Institute,
    Leader,
    LoginLog,
    Page,
    RegistrationApplication,
    Role,
    ServiceRequest,
    SiteSetting,
    Tag,
    User,
)
from app.db.session import get_db
from app.schemas import (
    APIResponse,
    AdminUserCreateIn,
    ArticleIn,
    BannerIn,
    CaseIn,
    CategoryIn,
    DownloadResourceIn,
    InstituteIn,
    LoginRequest,
    LeaderIn,
    PageIn,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RegisterRequest,
    ResetPasswordRequest,
    ReviewIn,
    ServiceRequestIn,
    SettingIn,
    SmsSendRequest,
    SmsLoginRequest,
    UserRejectIn,
    TagIn,
    UserOut,
    UserRoleUpdateIn,
)
from app.services.account_notifications import (
    send_admin_created_user_notification,
    send_registration_approved_notification,
    send_registration_rejected_notification,
    send_registration_submitted_notification,
)
from app.services.file_downloads import (
    DOWNLOAD_ACTION_DENIED,
    DOWNLOAD_ACTION_NOT_FOUND,
    DOWNLOAD_ACTION_PATH_INVALID,
    DOWNLOAD_ACTION_SUCCESS,
    audit_file_download,
    build_download_response,
    resolve_active_user_from_request,
    resolve_file_path,
    serialize_download_resource,
    serialize_file_record,
)
from app.services.password_reset import confirm_password_reset, create_password_reset_request
from app.services.password_policy import validate_password_policy
from app.services.request_context import RequestMeta, current_request_meta, extract_request_meta, get_client_ip, get_user_agent


router = APIRouter()


ALLOWED_UPLOAD_MIME_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "application/msword": {".doc"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
}
MAX_UPLOAD_SIZE = 52_428_800
CREATE_USER_ROLE_CODES = {"registered_user", "institute_editor"}
USER_STATUS_PENDING = "pending"
USER_STATUS_ACTIVE = "active"
USER_STATUS_REJECTED = "rejected"
USER_STATUS_DISABLED = "disabled"


def paginate(query, db: Session, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def serialize_category_ref(category: Category | None) -> dict | None:
    if not category:
        return None
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "type": category.type,
    }


def serialize_tag_ref(tag: Tag) -> dict:
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "type": tag.type,
        "color": tag.color,
        "enabled": tag.enabled,
    }


def article_tag_rows(db: Session, article_id: int) -> list[Tag]:
    return db.scalars(
        select(Tag)
        .join(ArticleTag, ArticleTag.tag_id == Tag.id)
        .where(ArticleTag.article_id == article_id)
        .order_by(Tag.name.asc(), Tag.id.asc())
    ).all()


def case_tag_rows(db: Session, case_id: int) -> list[Tag]:
    return db.scalars(
        select(Tag)
        .join(CaseTag, CaseTag.tag_id == Tag.id)
        .where(CaseTag.case_id == case_id)
        .order_by(Tag.name.asc(), Tag.id.asc())
    ).all()


def serialize_article(article: Article, db: Session | None = None) -> dict:
    category = db.get(Category, article.category_id) if db and article.category_id else None
    tags = article_tag_rows(db, article.id) if db else []
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "source": article.source,
        "author": article.author,
        "publish_at": article.publish_at,
        "status": article.status,
        "is_top": article.is_top,
        "seo_title": article.seo_title,
        "seo_description": article.seo_description,
        "seo_keywords": article.seo_keywords,
        "content_html": article.content_html,
        "attachments": article.attachments or [],
        "category_id": article.category_id,
        "category": serialize_category_ref(category),
        "category_name": category.name if category else None,
        "category_slug": category.slug if category else None,
        "cover_file_id": article.cover_file_id,
        "tag_ids": [tag.id for tag in tags],
        "tags": [serialize_tag_ref(tag) for tag in tags],
    }


def serialize_case(case: CaseStudy, db: Session | None = None) -> dict:
    category = db.get(Category, case.category_id) if db and case.category_id else None
    tags = case_tag_rows(db, case.id) if db else []
    return {
        "id": case.id,
        "title": case.title,
        "slug": case.slug,
        "summary": case.summary,
        "category_id": case.category_id,
        "category": serialize_category_ref(category),
        "category_name": category.name if category else None,
        "category_slug": category.slug if category else None,
        "partner_name": case.partner_name,
        "stage": case.stage,
        "highlights": case.highlights or [],
        "benefits": case.benefits,
        "content_html": case.content_html,
        "result_blocks": case.result_blocks or [],
        "publish_at": case.publish_at,
        "status": case.status,
        "cover_file_id": case.cover_file_id,
        "tag_ids": [tag.id for tag in tags],
        "tags": [serialize_tag_ref(tag) for tag in tags],
    }


def encode(value):
    return jsonable_encoder(value)


def write_audit_log(
    db: Session,
    user_id: int | None,
    module: str,
    action: str,
    object_type: str,
    object_id: str | None,
    detail: dict | None = None,
    *,
    result: str = "success",
    failure_reason: str | None = None,
    request_meta: RequestMeta | None = None,
):
    meta = request_meta or current_request_meta()
    db.add(
        AuditLog(
            user_id=user_id,
            module=module,
            action=action,
            object_type=object_type,
            object_id=object_id,
            detail_json=detail or {},
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
            path=meta.path,
            method=meta.method,
            result=result,
            failure_reason=failure_reason,
        )
    )


def write_login_log(
    db: Session,
    *,
    user_id: int | None,
    username: str | None,
    login_method: str,
    success: bool,
    request: Request,
    failure_reason: str | None = None,
) -> None:
    meta = extract_request_meta(request)
    db.add(
        LoginLog(
            user_id=user_id,
            username=username,
            login_method=login_method,
            ip_address=meta.ip_address,
            user_agent=meta.user_agent,
            path=meta.path,
            method=meta.method,
            success=success,
            failure_reason=failure_reason,
        )
    )
    write_audit_log(
        db,
        user_id,
        "auth",
        "login_success" if success else "login_failure",
        "login",
        username,
        {"login_method": login_method},
        result="success" if success else "failure",
        failure_reason=failure_reason,
        request_meta=meta,
    )


def api_error(http_status: int, code: int, message: str):
    return Response(
        content=APIResponse(code=code, message=message, data=None).model_dump_json(),
        status_code=http_status,
        media_type="application/json",
    )


def normalized_category_type(category_type: str | None) -> str | None:
    if category_type == "news":
        return "article"
    if category_type == "case":
        return "case"
    return category_type


def flush_or_slug_conflict(db: Session):
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return api_error(status.HTTP_409_CONFLICT, 409, "Slug already exists")
    return None


def commit_or_slug_conflict(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return api_error(status.HTTP_409_CONFLICT, 409, "Slug already exists")
    return None


def upload_validation_error(upload: UploadFile, contents: bytes):
    file_size = len(contents)
    file_extension = Path(upload.filename or "").suffix.lower()
    mime_type = upload.content_type or ""
    if file_size > MAX_UPLOAD_SIZE:
        return api_error(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 413, "File too large")
    if mime_type not in ALLOWED_UPLOAD_MIME_TYPES or file_extension not in ALLOWED_UPLOAD_MIME_TYPES[mime_type]:
        return api_error(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 415, "Unsupported file type")
    return None


def serialize_admin_user(user: User) -> dict:
    data = UserOut.model_validate(user).model_dump()
    data["role_code"] = user.role.code if user.role else None
    data["role_name"] = user.role.name if user.role else None
    return data


def serialize_current_user(user: User) -> dict:
    return serialize_admin_user(user)


def serialize_audit_log(log: AuditLog, actor: User | None = None) -> dict:
    data = encode(log)
    data["actor_username"] = actor.username if actor else None
    data["actor_real_name"] = actor.real_name if actor else None
    return data


def serialize_login_log(log: LoginLog) -> dict:
    return encode(log)


def serialize_download_resource_row(resource: DownloadResource, db: Session) -> dict:
    file_record = db.get(FileRecord, resource.file_id)
    return encode(serialize_download_resource(resource, file_record=file_record))


def get_role_by_code(db: Session, role_code: str) -> Role:
    role = db.scalar(select(Role).where(Role.code == role_code))
    if not role:
        raise HTTPException(status_code=400, detail="Invalid role")
    return role


def active_super_admin_count(db: Session) -> int:
    return db.scalar(
        select(func.count())
        .select_from(User)
        .join(Role, User.role_id == Role.id)
        .where(User.status == USER_STATUS_ACTIVE, Role.code == "super_admin")
    ) or 0


def ensure_not_last_active_super_admin(db: Session, target_user: User) -> None:
    if target_user.role.code == "super_admin" and target_user.status == USER_STATUS_ACTIVE and active_super_admin_count(db) <= 1:
        raise HTTPException(status_code=400, detail="Cannot modify the last active super admin")


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/healthz", response_model=APIResponse)
def healthz():
    return APIResponse(data={"status": "ok"})


@router.get(f"{settings.api_prefix}/public/categories", response_model=APIResponse)
def list_public_categories(type: str | None = None, db: Session = Depends(get_db)):
    normalized_type = normalized_category_type(type)
    query = select(Category).where(Category.enabled.is_(True)).order_by(Category.sort_order.asc(), Category.id.asc())
    if normalized_type:
        query = query.where(Category.type == normalized_type)
    rows = db.scalars(query).all()
    return APIResponse(data=[serialize_category_ref(row) for row in rows])


@router.get(f"{settings.api_prefix}/public/tags", response_model=APIResponse)
def list_public_tags(type: str | None = None, db: Session = Depends(get_db)):
    query = select(Tag).where(Tag.enabled.is_(True)).order_by(Tag.type.asc(), Tag.name.asc(), Tag.id.asc())
    if type:
        query = query.where(Tag.type == type)
    rows = db.scalars(query).all()
    return APIResponse(data=[serialize_tag_ref(row) for row in rows])


@router.get(f"{settings.api_prefix}/public/home", response_model=APIResponse)
def get_home(db: Session = Depends(get_db)):
    banners = db.scalars(select(Banner).where(Banner.is_enabled.is_(True)).order_by(Banner.sort_order.asc())).all()
    articles = db.scalars(
        select(Article)
        .where(Article.status == "published")
        .order_by(Article.is_top.desc(), Article.publish_at.desc())
        .limit(4)
    ).all()
    cases = db.scalars(
        select(CaseStudy).where(CaseStudy.status == "published").order_by(CaseStudy.publish_at.desc()).limit(3)
    ).all()
    pages = {item.page_key: item for item in db.scalars(select(Page).where(Page.status == "published")).all()}
    settings_map = {item.setting_key: item.setting_value for item in db.scalars(select(SiteSetting)).all()}
    return APIResponse(
        data={
            "banners": encode(banners),
            "news": [serialize_article(item, db) for item in articles],
            "cases": [serialize_case(item, db) for item in cases],
            "about": encode(pages.get("about")),
            "site_settings": settings_map,
        }
    )


@router.get(f"{settings.api_prefix}/public/news", response_model=APIResponse)
def list_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    category_slug: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    category_value = category or category_slug
    query = (
        select(Article)
        .join(Category, Article.category_id == Category.id, isouter=True)
        .where(Article.status == "published")
    )
    if category_value:
        query = query.where(Category.slug == category_value)
    if keyword:
        keyword_expr = f"%{keyword}%"
        query = query.where(or_(Article.title.like(keyword_expr), Article.summary.like(keyword_expr), Article.content_html.like(keyword_expr)))
    query = query.order_by(Article.is_top.desc(), Article.publish_at.desc(), Article.id.desc())
    result = paginate(query, db, page, page_size)
    result["items"] = [serialize_article(item, db) for item in result["items"]]
    return APIResponse(data=result)


@router.get(f"{settings.api_prefix}/public/news/{{slug}}", response_model=APIResponse)
def get_news_detail(slug: str, db: Session = Depends(get_db)):
    article = db.scalar(select(Article).where(Article.slug == slug, Article.status == "published"))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    related = db.scalars(
        select(Article)
        .where(Article.status == "published", Article.id != article.id)
        .order_by(Article.publish_at.desc())
        .limit(3)
    ).all()
    return APIResponse(data={"article": serialize_article(article, db), "related": [serialize_article(item, db) for item in related]})


@router.get(f"{settings.api_prefix}/public/cases", response_model=APIResponse)
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    category: str | None = None,
    keyword: str | None = None,
    db: Session = Depends(get_db),
):
    query = select(CaseStudy).where(CaseStudy.status == "published")
    if category:
        category_row = db.scalar(select(Category).where(Category.slug == category, Category.type == "case"))
        if category_row:
            query = query.where(CaseStudy.category_id == category_row.id)
        else:
            return APIResponse(data={"items": [], "page": page, "page_size": page_size, "total": 0})
    if keyword:
        keyword_expr = f"%{keyword}%"
        query = query.where(or_(CaseStudy.title.like(keyword_expr), CaseStudy.summary.like(keyword_expr), CaseStudy.content_html.like(keyword_expr)))
    query = query.order_by(CaseStudy.publish_at.desc(), CaseStudy.id.desc())
    result = paginate(query, db, page, page_size)
    result["items"] = [serialize_case(item, db) for item in result["items"]]
    return APIResponse(data=result)


@router.get(f"{settings.api_prefix}/public/cases/{{slug}}", response_model=APIResponse)
def get_case_detail(slug: str, db: Session = Depends(get_db)):
    case = db.scalar(select(CaseStudy).where(CaseStudy.slug == slug, CaseStudy.status == "published"))
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    related = db.scalars(
        select(CaseStudy)
        .where(CaseStudy.status == "published", CaseStudy.id != case.id)
        .order_by(CaseStudy.publish_at.desc())
        .limit(3)
    ).all()
    return APIResponse(data={"case": serialize_case(case, db), "related": [serialize_case(item, db) for item in related]})


@router.get(f"{settings.api_prefix}/public/pages/{{page_key}}", response_model=APIResponse)
def get_page(page_key: str, db: Session = Depends(get_db)):
    page = db.scalar(select(Page).where(Page.page_key == page_key, Page.status == "published"))
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return APIResponse(data=encode(page))


@router.get(f"{settings.api_prefix}/public/leaders", response_model=APIResponse)
def list_leaders(db: Session = Depends(get_db)):
    leaders = db.scalars(select(Leader).where(Leader.is_visible.is_(True)).order_by(Leader.sort_order.asc())).all()
    return APIResponse(data=encode(leaders))


@router.get(f"{settings.api_prefix}/public/institutes", response_model=APIResponse)
def list_institutes(db: Session = Depends(get_db)):
    institutes = db.scalars(select(Institute).where(Institute.status != "archived").order_by(Institute.sort_order.asc())).all()
    return APIResponse(data=encode(institutes))


@router.get(f"{settings.api_prefix}/public/institutes/{{slug}}", response_model=APIResponse)
def get_institute(slug: str, db: Session = Depends(get_db)):
    institute = db.scalar(select(Institute).where(Institute.slug == slug))
    if not institute:
        raise HTTPException(status_code=404, detail="Institute not found")
    return APIResponse(data=encode(institute))


@router.get(f"{settings.api_prefix}/public/settings", response_model=APIResponse)
def list_public_settings(db: Session = Depends(get_db)):
    data = {item.setting_key: item.setting_value for item in db.scalars(select(SiteSetting)).all()}
    return APIResponse(data=data)


@router.get(f"{settings.api_prefix}/public/downloads", response_model=APIResponse)
def list_public_downloads(
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = select(DownloadResource).where(DownloadResource.is_public.is_(True))
    if category:
        category_row = db.scalar(select(Category).where(Category.slug == category))
        if category_row:
            query = query.where(DownloadResource.category_id == category_row.id)
        else:
            return APIResponse(data={"items": [], "page": page, "page_size": page_size, "total": 0})
    query = query.order_by(DownloadResource.sort_order.asc(), DownloadResource.created_at.desc())
    result = paginate(query, db, page, page_size)
    result["items"] = [serialize_download_resource_row(item, db) for item in result["items"]]
    return APIResponse(data=result)


@router.get(f"{settings.api_prefix}/public/downloads/{{resource_id}}/download")
def download_public_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    resource = db.get(DownloadResource, resource_id)
    if not resource:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_NOT_FOUND,
            result="failure",
            resource_id=resource_id,
            reason="resource_not_found",
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Download resource not found")
    file_record = db.get(FileRecord, resource.file_id)
    if not resource.is_public:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_DENIED,
            result="failure",
            resource_id=resource.id,
            file_record=file_record,
            reason="protected_resource",
            is_public=resource.is_public,
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Download requires login")
    if not file_record:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_NOT_FOUND,
            result="failure",
            resource_id=resource.id,
            reason="file_not_found",
            is_public=resource.is_public,
        )
        db.commit()
        raise HTTPException(status_code=404, detail="File not found")
    try:
        resolved_path = resolve_file_path(file_record)
    except HTTPException as exc:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_PATH_INVALID if exc.status_code == 403 else DOWNLOAD_ACTION_NOT_FOUND,
            result="failure",
            resource_id=resource.id,
            file_record=file_record,
            reason="path_invalid" if exc.status_code == 403 else "file_not_found",
            is_public=resource.is_public,
        )
        db.commit()
        raise
    resource.download_count = (resource.download_count or 0) + 1
    audit_file_download(
        db,
        request=request,
        action=DOWNLOAD_ACTION_SUCCESS,
        result="success",
        resource_id=resource.id,
        file_record=file_record,
        is_public=resource.is_public,
    )
    db.commit()
    return build_download_response(file_record, resolved_path)


@router.get(f"{settings.api_prefix}/downloads/{{resource_id}}/download")
def download_protected_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    current_user, auth_failure = resolve_active_user_from_request(db, request)
    if not current_user:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_DENIED,
            result="failure",
            resource_id=resource_id,
            reason=auth_failure or "unauthorized",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    resource = db.get(DownloadResource, resource_id)
    if not resource:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_NOT_FOUND,
            result="failure",
            resource_id=resource_id,
            user=current_user,
            actor_type="user",
            reason="resource_not_found",
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Download resource not found")
    file_record = db.get(FileRecord, resource.file_id)
    if not file_record:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_NOT_FOUND,
            result="failure",
            resource_id=resource.id,
            user=current_user,
            actor_type="user",
            reason="file_not_found",
            is_public=resource.is_public,
        )
        db.commit()
        raise HTTPException(status_code=404, detail="File not found")
    try:
        resolved_path = resolve_file_path(file_record)
    except HTTPException as exc:
        audit_file_download(
            db,
            request=request,
            action=DOWNLOAD_ACTION_PATH_INVALID if exc.status_code == 403 else DOWNLOAD_ACTION_NOT_FOUND,
            result="failure",
            resource_id=resource.id,
            file_record=file_record,
            user=current_user,
            actor_type="user",
            reason="path_invalid" if exc.status_code == 403 else "file_not_found",
            is_public=resource.is_public,
        )
        db.commit()
        raise
    resource.download_count = (resource.download_count or 0) + 1
    audit_file_download(
        db,
        request=request,
        action=DOWNLOAD_ACTION_SUCCESS,
        result="success",
        resource_id=resource.id,
        file_record=file_record,
        user=current_user,
        actor_type="user",
        is_public=resource.is_public,
    )
    db.commit()
    return build_download_response(file_record, resolved_path)


@router.post(f"{settings.api_prefix}/public/inquiries", response_model=APIResponse)
def create_inquiry(payload: ServiceRequestIn, db: Session = Depends(get_db)):
    service_request = ServiceRequest(
        type=payload.type,
        subject=payload.subject,
        contact_name=payload.contact_name,
        contact_mobile=payload.contact_mobile,
        contact_email=payload.contact_email,
        organization=payload.organization,
        content=payload.content,
    )
    db.add(service_request)
    db.commit()
    db.refresh(service_request)
    return APIResponse(data=encode(service_request))


@router.post(f"{settings.api_prefix}/auth/sms-send", response_model=APIResponse)
def send_sms_code(payload: SmsSendRequest):
    # TODO: Replace this stub with a real SMS provider integration and rate limiting.
    print(f"SMS send requested for mobile={payload.mobile}")
    return APIResponse(data=None)


@router.post(f"{settings.api_prefix}/auth/reset-password", response_model=APIResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if payload.code != settings.sms_test_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    user = db.scalar(select(User).where(User.mobile == payload.mobile))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return APIResponse(data=None)


@router.post(f"{settings.api_prefix}/auth/password-reset/request", response_model=APIResponse)
def request_password_reset(payload: PasswordResetRequestIn, request: Request, db: Session = Depends(get_db)):
    data = create_password_reset_request(
        db,
        email_or_username=payload.email_or_username,
        request_ip=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    return APIResponse(data=data)


@router.post(f"{settings.api_prefix}/auth/password-reset/confirm", response_model=APIResponse)
def confirm_password_reset_route(payload: PasswordResetConfirmIn, db: Session = Depends(get_db)):
    return APIResponse(data=confirm_password_reset(db, token=payload.token, new_password=payload.new_password))


@router.post(f"{settings.api_prefix}/auth/login/password", response_model=APIResponse)
def login_password(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    password_ok = bool(user and verify_password(payload.password, user.password_hash))
    if not user or not password_ok or user.status != "active":
        failure_reason = "inactive_user" if user and password_ok and user.status != "active" else "invalid_credentials"
        write_login_log(
            db,
            user_id=user.id if user else None,
            username=payload.username,
            login_method="password",
            success=False,
            request=request,
            failure_reason=failure_reason,
        )
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    write_login_log(
        db,
        user_id=user.id,
        username=user.username,
        login_method="password",
        success=True,
        request=request,
    )
    db.commit()
    return APIResponse(data={"access_token": token, "token_type": "bearer", "user": serialize_current_user(user)})


@router.post(f"{settings.api_prefix}/auth/login/sms", response_model=APIResponse)
def login_sms(payload: SmsLoginRequest, request: Request, db: Session = Depends(get_db)):
    if payload.code != settings.sms_test_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    user = db.scalar(select(User).where(User.mobile == payload.mobile))
    if not user or user.status != "active":
        raise HTTPException(status_code=400, detail="User is not active")
    token = create_access_token(str(user.id))
    db.add(LoginLog(user_id=user.id, username=user.username, login_method="sms", ip_address=request.client.host if request.client else None, success=True))
    db.commit()
    return APIResponse(data={"access_token": token, "token_type": "bearer", "user": serialize_current_user(user)})


@router.post(f"{settings.api_prefix}/auth/register", response_model=APIResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    validate_password_policy(payload.password)
    if db.scalar(select(User).where(User.mobile == payload.mobile)):
        raise HTTPException(status_code=400, detail="Mobile already registered")
    role = db.scalar(select(Role).where(Role.code == "registered_user"))
    if not role:
        raise HTTPException(status_code=500, detail="Default role missing")
    user = User(
        username=payload.mobile,
        mobile=payload.mobile,
        email=payload.email,
        password_hash=hash_password(payload.password),
        real_name=payload.real_name,
        organization=payload.organization,
        expertise=payload.expertise,
        status="pending",
        role_id=role.id,
    )
    db.add(user)
    db.flush()
    db.add(RegistrationApplication(user_id=user.id, review_status="pending"))
    write_audit_log(
        db,
        user.id,
        "auth",
        "registration_submitted",
        "user",
        str(user.id),
        {"status": "pending"},
    )
    send_registration_submitted_notification(db, user)
    db.commit()
    return APIResponse(data={"status": "pending_review", "user_id": user.id})


@router.get(f"{settings.api_prefix}/auth/me", response_model=APIResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse(data=serialize_current_user(current_user))


@router.get(f"{settings.api_prefix}/admin/dashboard", response_model=APIResponse)
def get_dashboard(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    data = {
        "articles": db.scalar(select(func.count()).select_from(Article)),
        "cases": db.scalar(select(func.count()).select_from(CaseStudy)),
        "pages": db.scalar(select(func.count()).select_from(Page)),
        "pending_users": db.scalar(select(func.count()).select_from(User).where(User.status == "pending")),
        "service_requests": db.scalar(select(func.count()).select_from(ServiceRequest)),
    }
    return APIResponse(data=data)


@router.get(f"{settings.api_prefix}/admin/articles", response_model=APIResponse)
def admin_list_articles(page: int = 1, page_size: int = 20, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    result = paginate(select(Article).order_by(Article.updated_at.desc(), Article.id.desc()), db, page, page_size)
    result["items"] = [serialize_article(item, db) for item in result["items"]]
    return APIResponse(data=result)


@router.post(f"{settings.api_prefix}/admin/articles", response_model=APIResponse)
def admin_create_article(payload: ArticleIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    article = Article(**payload.model_dump(exclude={"tag_ids"}))
    db.add(article)
    conflict_response = flush_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    for tag_id in payload.tag_ids:
        db.add(ArticleTag(article_id=article.id, tag_id=tag_id))
    write_audit_log(db, current_user.id, "articles", "create", "article", str(article.id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(article)
    return APIResponse(data=serialize_article(article, db))


@router.put(f"{settings.api_prefix}/admin/articles/{{article_id}}", response_model=APIResponse)
def admin_update_article(article_id: int, payload: ArticleIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    for key, value in payload.model_dump(exclude={"tag_ids"}).items():
        setattr(article, key, value)
    db.execute(delete(ArticleTag).where(ArticleTag.article_id == article.id))
    for tag_id in payload.tag_ids:
        db.add(ArticleTag(article_id=article.id, tag_id=tag_id))
    write_audit_log(db, current_user.id, "articles", "update", "article", str(article.id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(article)
    return APIResponse(data=serialize_article(article, db))


@router.get(f"{settings.api_prefix}/admin/cases", response_model=APIResponse)
def admin_list_cases(page: int = 1, page_size: int = 20, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    result = paginate(select(CaseStudy).order_by(CaseStudy.updated_at.desc(), CaseStudy.id.desc()), db, page, page_size)
    result["items"] = [serialize_case(item, db) for item in result["items"]]
    return APIResponse(data=result)


@router.post(f"{settings.api_prefix}/admin/cases", response_model=APIResponse)
def admin_create_case(payload: CaseIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    case = CaseStudy(**payload.model_dump(exclude={"tag_ids"}))
    db.add(case)
    conflict_response = flush_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    for tag_id in payload.tag_ids:
        db.add(CaseTag(case_id=case.id, tag_id=tag_id))
    write_audit_log(db, current_user.id, "cases", "create", "case", str(case.id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(case)
    return APIResponse(data=serialize_case(case, db))


@router.put(f"{settings.api_prefix}/admin/cases/{{case_id}}", response_model=APIResponse)
def admin_update_case(case_id: int, payload: CaseIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    case = db.get(CaseStudy, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    for key, value in payload.model_dump(exclude={"tag_ids"}).items():
        setattr(case, key, value)
    db.execute(delete(CaseTag).where(CaseTag.case_id == case.id))
    for tag_id in payload.tag_ids:
        db.add(CaseTag(case_id=case.id, tag_id=tag_id))
    write_audit_log(db, current_user.id, "cases", "update", "case", str(case.id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(case)
    return APIResponse(data=serialize_case(case, db))


@router.get(f"{settings.api_prefix}/admin/pages", response_model=APIResponse)
def admin_list_pages(page_key: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    query = select(Page).order_by(Page.page_key.asc(), Page.id.asc())
    if page_key:
        query = query.where(Page.page_key == page_key)
    return APIResponse(data=encode(db.scalars(query).all()))


@router.post(f"{settings.api_prefix}/admin/pages", response_model=APIResponse)
def admin_create_page(payload: PageIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = Page(**payload.model_dump())
    db.add(page)
    write_audit_log(db, current_user.id, "pages", "create", "page", payload.page_key)
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(page)
    return APIResponse(data=encode(page))


@router.put(f"{settings.api_prefix}/admin/pages/{{page_id}}", response_model=APIResponse)
def admin_update_page(page_id: int, payload: PageIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    page = db.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    for key, value in payload.model_dump().items():
        setattr(page, key, value)
    write_audit_log(db, current_user.id, "pages", "update", "page", str(page_id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(page)
    return APIResponse(data=encode(page))


@router.get(f"{settings.api_prefix}/admin/banners", response_model=APIResponse)
def admin_list_banners(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return APIResponse(data=encode(db.scalars(select(Banner).order_by(Banner.sort_order.asc(), Banner.id.asc())).all()))


@router.post(f"{settings.api_prefix}/admin/banners", response_model=APIResponse)
def admin_create_banner(payload: BannerIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    banner = Banner(**payload.model_dump())
    db.add(banner)
    write_audit_log(db, current_user.id, "banners", "create", "banner", None)
    db.commit()
    db.refresh(banner)
    return APIResponse(data=encode(banner))


@router.put(f"{settings.api_prefix}/admin/banners/{{banner_id}}", response_model=APIResponse)
def admin_update_banner(banner_id: int, payload: BannerIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    banner = db.get(Banner, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    for key, value in payload.model_dump().items():
        setattr(banner, key, value)
    write_audit_log(db, current_user.id, "banners", "update", "banner", str(banner_id))
    db.commit()
    db.refresh(banner)
    return APIResponse(data=encode(banner))


@router.get(f"{settings.api_prefix}/admin/categories", response_model=APIResponse)
def admin_list_categories(type: str | None = None, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    normalized_type = normalized_category_type(type)
    query = select(Category).order_by(Category.type.asc(), Category.sort_order.asc(), Category.id.asc())
    if normalized_type:
        query = query.where(Category.type == normalized_type)
    return APIResponse(data=encode(db.scalars(query).all()))


@router.post(f"{settings.api_prefix}/admin/categories", response_model=APIResponse)
def admin_create_category(payload: CategoryIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = Category(**payload.model_dump())
    db.add(category)
    write_audit_log(db, current_user.id, "categories", "create", "category", payload.slug)
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(category)
    return APIResponse(data=encode(category))


@router.put(f"{settings.api_prefix}/admin/categories/{{category_id}}", response_model=APIResponse)
def admin_update_category(category_id: int, payload: CategoryIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in payload.model_dump().items():
        setattr(category, key, value)
    write_audit_log(db, current_user.id, "categories", "update", "category", str(category_id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(category)
    return APIResponse(data=encode(category))


@router.get(f"{settings.api_prefix}/admin/tags", response_model=APIResponse)
def admin_list_tags(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return APIResponse(data=encode(db.scalars(select(Tag).order_by(Tag.name.asc())).all()))


@router.post(f"{settings.api_prefix}/admin/tags", response_model=APIResponse)
def admin_create_tag(payload: TagIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tag = Tag(**payload.model_dump())
    db.add(tag)
    write_audit_log(db, current_user.id, "tags", "create", "tag", None)
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(tag)
    return APIResponse(data=encode(tag))


@router.put(f"{settings.api_prefix}/admin/tags/{{tag_id}}", response_model=APIResponse)
def admin_update_tag(tag_id: int, payload: TagIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    for key, value in payload.model_dump().items():
        setattr(tag, key, value)
    write_audit_log(db, current_user.id, "tags", "update", "tag", str(tag_id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(tag)
    return APIResponse(data=encode(tag))


@router.get(f"{settings.api_prefix}/admin/leaders", response_model=APIResponse)
def admin_list_leaders(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return APIResponse(data=encode(db.scalars(select(Leader).order_by(Leader.sort_order.asc())).all()))


@router.post(f"{settings.api_prefix}/admin/leaders", response_model=APIResponse)
def admin_create_leader(payload: LeaderIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    leader = Leader(**payload.model_dump())
    db.add(leader)
    db.flush()
    write_audit_log(db, current_user.id, "leaders", "create", "leader", str(leader.id))
    db.commit()
    db.refresh(leader)
    return APIResponse(data=encode(leader))


@router.put(f"{settings.api_prefix}/admin/leaders/{{leader_id}}", response_model=APIResponse)
def admin_update_leader(leader_id: int, payload: LeaderIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    leader = db.get(Leader, leader_id)
    if not leader:
        raise HTTPException(status_code=404, detail="Leader not found")
    for key, value in payload.model_dump().items():
        setattr(leader, key, value)
    write_audit_log(db, current_user.id, "leaders", "update", "leader", str(leader_id))
    db.commit()
    db.refresh(leader)
    return APIResponse(data=encode(leader))


@router.get(f"{settings.api_prefix}/admin/institutes", response_model=APIResponse)
def admin_list_institutes(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return APIResponse(data=encode(db.scalars(select(Institute).order_by(Institute.sort_order.asc())).all()))


@router.post(f"{settings.api_prefix}/admin/institutes", response_model=APIResponse)
def admin_create_institute(payload: InstituteIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    institute = Institute(**payload.model_dump())
    db.add(institute)
    conflict_response = flush_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    write_audit_log(db, current_user.id, "institutes", "create", "institute", str(institute.id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(institute)
    return APIResponse(data=encode(institute))


@router.put(f"{settings.api_prefix}/admin/institutes/{{institute_id}}", response_model=APIResponse)
def admin_update_institute(institute_id: int, payload: InstituteIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    institute = db.get(Institute, institute_id)
    if not institute:
        raise HTTPException(status_code=404, detail="Institute not found")
    for key, value in payload.model_dump().items():
        setattr(institute, key, value)
    write_audit_log(db, current_user.id, "institutes", "update", "institute", str(institute_id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(institute)
    return APIResponse(data=encode(institute))


@router.get(f"{settings.api_prefix}/admin/files", response_model=APIResponse)
def admin_list_files(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    files = db.scalars(select(FileRecord).order_by(FileRecord.created_at.desc())).all()
    return APIResponse(data=encode([serialize_file_record(item) for item in files]))


@router.post(f"{settings.api_prefix}/admin/files/upload", response_model=APIResponse)
async def admin_upload_file(
    upload: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    storage_root = Path(settings.storage_root)
    upload_root = storage_root / settings.upload_dir
    upload_root.mkdir(parents=True, exist_ok=True)
    extension = Path(upload.filename or "").suffix
    safe_name = f"{uuid4().hex}{extension}"
    destination = upload_root / safe_name
    contents = await upload.read()
    validation_error = upload_validation_error(upload, contents)
    if validation_error:
        return validation_error
    destination.write_bytes(contents)
    record = FileRecord(
        origin_name=upload.filename or safe_name,
        storage_path=str(destination.relative_to(storage_root)),
        mime_type=upload.content_type or "application/octet-stream",
        size=len(contents),
        owner_id=current_user.id,
    )
    db.add(record)
    db.flush()
    write_audit_log(db, current_user.id, "files", "create", "file", str(record.id))
    db.commit()
    db.refresh(record)
    return APIResponse(data=encode(serialize_file_record(record)))


@router.get(f"{settings.api_prefix}/admin/settings", response_model=APIResponse)
def admin_list_settings(_: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    return APIResponse(data=encode(db.scalars(select(SiteSetting).order_by(SiteSetting.group_name.asc(), SiteSetting.setting_key.asc())).all()))


@router.get(f"{settings.api_prefix}/admin/settings/site", response_model=APIResponse)
def admin_get_site_settings(_: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(SiteSetting).order_by(SiteSetting.group_name.asc(), SiteSetting.setting_key.asc())).all()
    return APIResponse(data={row.setting_key: row.setting_value for row in rows})


@router.put(f"{settings.api_prefix}/admin/settings/{{setting_key}}", response_model=APIResponse)
def admin_upsert_setting(setting_key: str, payload: SettingIn, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    setting = db.scalar(select(SiteSetting).where(SiteSetting.setting_key == setting_key))
    if setting:
        setting.setting_value = payload.setting_value
        setting.group_name = payload.group_name
    else:
        setting = SiteSetting(setting_key=setting_key, setting_value=payload.setting_value, group_name=payload.group_name)
        db.add(setting)
    write_audit_log(db, current_user.id, "settings", "upsert", "setting", setting_key)
    db.commit()
    db.refresh(setting)
    return APIResponse(data=encode(setting))


@router.get(f"{settings.api_prefix}/admin/users", response_model=APIResponse)
def admin_list_users(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.created_at.desc())
    if status:
        query = query.where(User.status == status)
    result = paginate(query, db, page, page_size)
    result["items"] = [serialize_admin_user(item) for item in result["items"]]
    return APIResponse(data=result)


@router.get(f"{settings.api_prefix}/admin/roles", response_model=APIResponse)
def admin_list_roles(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    roles = db.scalars(select(Role).order_by(Role.id.asc())).all()
    return APIResponse(
        data=[
            {"id": role.id, "code": role.code, "name": role.name, "description": role.description}
            for role in roles
        ]
    )


@router.get(f"{settings.api_prefix}/admin/users/pending", response_model=APIResponse)
def admin_list_pending_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).where(User.status == "pending").order_by(User.created_at.desc())).all()
    return APIResponse(data=[serialize_admin_user(item) for item in users])


@router.post(f"{settings.api_prefix}/admin/users", response_model=APIResponse)
def admin_create_user(payload: AdminUserCreateIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    validate_password_policy(payload.password)
    role_code = payload.role_code.strip()
    if role_code not in CREATE_USER_ROLE_CODES:
        raise HTTPException(status_code=400, detail="Role is not allowed for institution user creation")
    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=400, detail="Username already exists")
    if payload.mobile and db.scalar(select(User).where(User.mobile == payload.mobile)):
        raise HTTPException(status_code=400, detail="Mobile already exists")
    if payload.email and db.scalar(select(User).where(func.lower(User.email) == payload.email.lower())):
        raise HTTPException(status_code=400, detail="Email already exists")

    role = get_role_by_code(db, role_code)
    user = User(
        username=payload.username,
        mobile=payload.mobile,
        email=str(payload.email) if payload.email else None,
        password_hash=hash_password(payload.password),
        real_name=payload.real_name,
        organization=payload.organization,
        expertise=payload.expertise,
        status=USER_STATUS_ACTIVE,
        role_id=role.id,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="User identity already exists") from None
    write_audit_log(
        db,
        current_user.id,
        "users",
        "create",
        "user",
        str(user.id),
        {"role_code": role.code, "status": USER_STATUS_ACTIVE},
    )
    send_admin_created_user_notification(db, user)
    db.commit()
    db.refresh(user)
    return APIResponse(data=serialize_admin_user(user))


@router.post(f"{settings.api_prefix}/admin/users/{{user_id}}/approve", response_model=APIResponse)
def admin_approve_user(user_id: int, payload: ReviewIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.status != USER_STATUS_PENDING:
        raise HTTPException(status_code=400, detail="Only pending users can be approved")
    application = db.scalar(select(RegistrationApplication).where(RegistrationApplication.user_id == user_id))
    user.status = USER_STATUS_ACTIVE
    if application:
        application.review_status = "approved"
        application.review_comment = payload.review_comment
        application.reviewed_by = current_user.id
        application.reviewed_at = datetime.now(UTC)
    write_audit_log(db, current_user.id, "users", "approve", "user", str(user_id), {"status": USER_STATUS_ACTIVE})
    send_registration_approved_notification(db, user)
    db.commit()
    db.refresh(user)
    return APIResponse(data=serialize_admin_user(user))


@router.post(f"{settings.api_prefix}/admin/users/{{user_id}}/reject", response_model=APIResponse)
def admin_reject_user(user_id: int, payload: UserRejectIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.status != USER_STATUS_PENDING:
        raise HTTPException(status_code=400, detail="Only pending users can be rejected")
    reason = payload.reason.strip()
    application = db.scalar(select(RegistrationApplication).where(RegistrationApplication.user_id == user_id))
    user.status = USER_STATUS_REJECTED
    if application:
        application.review_status = "rejected"
        application.review_comment = reason
        application.reviewed_by = current_user.id
        application.reviewed_at = datetime.now(UTC)
    write_audit_log(
        db,
        current_user.id,
        "users",
        "reject",
        "user",
        str(user_id),
        {"status": USER_STATUS_REJECTED, "has_reason": True},
    )
    send_registration_rejected_notification(db, user, reason)
    db.commit()
    db.refresh(user)
    return APIResponse(data=serialize_admin_user(user))


@router.post(f"{settings.api_prefix}/admin/users/{{user_id}}/disable", response_model=APIResponse)
def admin_disable_user(user_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    if user.status != USER_STATUS_ACTIVE:
        raise HTTPException(status_code=400, detail="Only active users can be disabled")
    ensure_not_last_active_super_admin(db, user)
    user.status = USER_STATUS_DISABLED
    write_audit_log(db, current_user.id, "users", "disable", "user", str(user_id), {"status": USER_STATUS_DISABLED})
    db.commit()
    db.refresh(user)
    return APIResponse(data=serialize_admin_user(user))


@router.post(f"{settings.api_prefix}/admin/users/{{user_id}}/enable", response_model=APIResponse)
def admin_enable_user(user_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    if user.status != USER_STATUS_DISABLED:
        raise HTTPException(status_code=400, detail="Only disabled users can be enabled")
    user.status = USER_STATUS_ACTIVE
    write_audit_log(db, current_user.id, "users", "enable", "user", str(user_id), {"status": USER_STATUS_ACTIVE})
    db.commit()
    db.refresh(user)
    return APIResponse(data=serialize_admin_user(user))


@router.put(f"{settings.api_prefix}/admin/users/{{user_id}}/role", response_model=APIResponse)
def admin_update_user_role(user_id: int, payload: UserRoleUpdateIn, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)):
    user = get_user_or_404(db, user_id)
    role = get_role_by_code(db, payload.role_code.strip())
    old_role_code = user.role.code
    if user.id == current_user.id and role.code != "super_admin":
        raise HTTPException(status_code=400, detail="Cannot remove your own super admin role")
    if old_role_code == "super_admin" and role.code != "super_admin":
        ensure_not_last_active_super_admin(db, user)
    user.role_id = role.id
    write_audit_log(
        db,
        current_user.id,
        "users",
        "assign_role",
        "user",
        str(user_id),
        {"old_role_code": old_role_code, "new_role_code": role.code},
    )
    db.commit()
    db.refresh(user)
    return APIResponse(data=serialize_admin_user(user))


@router.get(f"{settings.api_prefix}/admin/downloads", response_model=APIResponse)
def admin_list_downloads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(DownloadResource).order_by(DownloadResource.sort_order.asc(), DownloadResource.created_at.desc())
    result = paginate(query, db, page, page_size)
    result["items"] = [serialize_download_resource_row(item, db) for item in result["items"]]
    return APIResponse(data=result)


@router.post(f"{settings.api_prefix}/admin/downloads", response_model=APIResponse)
def admin_create_download(payload: DownloadResourceIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    resource = DownloadResource(**payload.model_dump())
    db.add(resource)
    conflict_response = flush_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    write_audit_log(db, current_user.id, "downloads", "create", "download_resource", str(resource.id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(resource)
    return APIResponse(data=serialize_download_resource_row(resource, db))


@router.put(f"{settings.api_prefix}/admin/downloads/{{resource_id}}", response_model=APIResponse)
def admin_update_download(resource_id: int, payload: DownloadResourceIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    resource = db.get(DownloadResource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="Download resource not found")
    for key, value in payload.model_dump().items():
        setattr(resource, key, value)
    write_audit_log(db, current_user.id, "downloads", "update", "download_resource", str(resource_id))
    conflict_response = commit_or_slug_conflict(db)
    if conflict_response:
        return conflict_response
    db.refresh(resource)
    return APIResponse(data=serialize_download_resource_row(resource, db))


@router.get(f"{settings.api_prefix}/admin/service-requests", response_model=APIResponse)
def admin_list_service_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(ServiceRequest).order_by(ServiceRequest.created_at.desc(), ServiceRequest.id.desc())
    return APIResponse(data=encode(paginate(query, db, page, page_size)))


@router.get(f"{settings.api_prefix}/admin/audit-logs", response_model=APIResponse)
def admin_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ip: str | None = None,
    username: str | None = None,
    action: str | None = None,
    module: str | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if ip and ip.strip():
        query = query.where(AuditLog.ip_address.ilike(f"%{ip.strip()}%"))
    if action and action.strip():
        query = query.where(AuditLog.action.ilike(f"%{action.strip()}%"))
    if module and module.strip():
        query = query.where(AuditLog.module.ilike(f"%{module.strip()}%"))
    if username and username.strip():
        keyword = f"%{username.strip()}%"
        actor_ids = select(User.id).where(
            or_(
                User.username.ilike(keyword),
                User.real_name.ilike(keyword),
                User.email.ilike(keyword),
                User.mobile.ilike(keyword),
            )
        )
        query = query.where(AuditLog.user_id.in_(actor_ids))
    result = paginate(query, db, page, page_size)
    actor_ids = {item.user_id for item in result["items"] if item.user_id}
    actors = {user.id: user for user in db.scalars(select(User).where(User.id.in_(actor_ids))).all()} if actor_ids else {}
    result["items"] = [serialize_audit_log(item, actors.get(item.user_id)) for item in result["items"]]
    return APIResponse(data=result)


@router.get(f"{settings.api_prefix}/admin/login-logs", response_model=APIResponse)
def admin_login_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ip: str | None = None,
    username: str | None = None,
    action: str | None = None,
    success: bool | None = None,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(LoginLog).order_by(LoginLog.created_at.desc(), LoginLog.id.desc())
    if ip and ip.strip():
        query = query.where(LoginLog.ip_address.ilike(f"%{ip.strip()}%"))
    if username and username.strip():
        query = query.where(LoginLog.username.ilike(f"%{username.strip()}%"))
    if action and action.strip():
        query = query.where(LoginLog.login_method.ilike(f"%{action.strip()}%"))
    if success is not None:
        query = query.where(LoginLog.success.is_(success))
    result = paginate(query, db, page, page_size)
    result["items"] = [serialize_login_log(item) for item in result["items"]]
    return APIResponse(data=result)
