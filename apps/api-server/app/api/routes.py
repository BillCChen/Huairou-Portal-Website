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
    ArticleIn,
    AuthTokenOut,
    BannerIn,
    CaseIn,
    CategoryIn,
    DownloadResourceIn,
    InstituteIn,
    LoginRequest,
    LeaderIn,
    PageIn,
    RegisterRequest,
    ResetPasswordRequest,
    ReviewIn,
    ServiceRequestIn,
    SettingIn,
    SmsSendRequest,
    SmsLoginRequest,
    TagIn,
    UserOut,
)


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


def paginate(query, db: Session, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "page": page, "page_size": page_size, "total": total}


def serialize_article(article: Article) -> dict:
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
        "cover_file_id": article.cover_file_id,
    }


def serialize_case(case: CaseStudy) -> dict:
    return {
        "id": case.id,
        "title": case.title,
        "slug": case.slug,
        "summary": case.summary,
        "category_id": case.category_id,
        "partner_name": case.partner_name,
        "stage": case.stage,
        "highlights": case.highlights or [],
        "benefits": case.benefits,
        "content_html": case.content_html,
        "result_blocks": case.result_blocks or [],
        "publish_at": case.publish_at,
        "status": case.status,
        "cover_file_id": case.cover_file_id,
    }


def encode(value):
    return jsonable_encoder(value)


def write_audit_log(db: Session, user_id: int | None, module: str, action: str, object_type: str, object_id: str | None):
    db.add(
        AuditLog(
            user_id=user_id,
            module=module,
            action=action,
            object_type=object_type,
            object_id=object_id,
            detail_json={},
        )
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
    return APIResponse(data=[{"id": row.id, "name": row.name, "slug": row.slug, "type": row.type} for row in rows])


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
            "news": [serialize_article(item) for item in articles],
            "cases": [serialize_case(item) for item in cases],
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
    result["items"] = [serialize_article(item) for item in result["items"]]
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
    return APIResponse(data={"article": serialize_article(article), "related": [serialize_article(item) for item in related]})


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
    result["items"] = [serialize_case(item) for item in result["items"]]
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
    return APIResponse(data={"case": serialize_case(case), "related": [serialize_case(item) for item in related]})


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
    return APIResponse(data=encode(paginate(query, db, page, page_size)))


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


@router.post(f"{settings.api_prefix}/auth/login/password", response_model=APIResponse)
def login_password(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == payload.username))
    if not user or not verify_password(payload.password, user.password_hash) or user.status != "active":
        db.add(LoginLog(username=payload.username, login_method="password", ip_address=request.client.host if request.client else None, success=False))
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    db.add(LoginLog(user_id=user.id, username=user.username, login_method="password", ip_address=request.client.host if request.client else None, success=True))
    db.commit()
    return APIResponse(data=AuthTokenOut(access_token=token, user=UserOut.model_validate(user)))


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
    return APIResponse(data=AuthTokenOut(access_token=token, user=UserOut.model_validate(user)))


@router.post(f"{settings.api_prefix}/auth/register", response_model=APIResponse)
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)):
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
    db.commit()
    return APIResponse(data={"status": "pending_review", "user_id": user.id})


@router.get(f"{settings.api_prefix}/auth/me", response_model=APIResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse(data=UserOut.model_validate(current_user))


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
    result["items"] = [serialize_article(item) for item in result["items"]]
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
    return APIResponse(data=serialize_article(article))


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
    return APIResponse(data=serialize_article(article))


@router.get(f"{settings.api_prefix}/admin/cases", response_model=APIResponse)
def admin_list_cases(page: int = 1, page_size: int = 20, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    result = paginate(select(CaseStudy).order_by(CaseStudy.updated_at.desc(), CaseStudy.id.desc()), db, page, page_size)
    result["items"] = [serialize_case(item) for item in result["items"]]
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
    return APIResponse(data=serialize_case(case))


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
    return APIResponse(data=serialize_case(case))


@router.get(f"{settings.api_prefix}/admin/pages", response_model=APIResponse)
def admin_list_pages(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return APIResponse(data=encode(db.scalars(select(Page).order_by(Page.page_key.asc())).all()))


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
    db.commit()
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
    return APIResponse(data=encode(db.scalars(select(FileRecord).order_by(FileRecord.created_at.desc())).all()))


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
    return APIResponse(data=encode(record))


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
    result["items"] = [UserOut.model_validate(item).model_dump() for item in result["items"]]
    return APIResponse(data=result)


@router.get(f"{settings.api_prefix}/admin/users/pending", response_model=APIResponse)
def admin_list_pending_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.scalars(select(User).where(User.status == "pending").order_by(User.created_at.desc())).all()
    return APIResponse(data=[UserOut.model_validate(item) for item in users])


@router.post(f"{settings.api_prefix}/admin/users/{{user_id}}/approve", response_model=APIResponse)
def admin_approve_user(user_id: int, payload: ReviewIn, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    application = db.scalar(select(RegistrationApplication).where(RegistrationApplication.user_id == user_id))
    user.status = "active"
    if application:
        application.review_status = "approved"
        application.review_comment = payload.review_comment
        application.reviewed_by = current_user.id
        application.reviewed_at = datetime.now(UTC)
    write_audit_log(db, current_user.id, "users", "approve", "user", str(user_id))
    db.commit()
    return APIResponse(data={"status": "active"})


@router.get(f"{settings.api_prefix}/admin/downloads", response_model=APIResponse)
def admin_list_downloads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(DownloadResource).order_by(DownloadResource.sort_order.asc(), DownloadResource.created_at.desc())
    return APIResponse(data=encode(paginate(query, db, page, page_size)))


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
    return APIResponse(data=encode(resource))


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
    return APIResponse(data=encode(resource))


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
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    return APIResponse(data=encode(paginate(query, db, page, page_size)))


@router.get(f"{settings.api_prefix}/admin/login-logs", response_model=APIResponse)
def admin_login_logs(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    logs = db.scalars(select(LoginLog).order_by(LoginLog.created_at.desc()).limit(200)).all()
    return APIResponse(data=encode(logs))
