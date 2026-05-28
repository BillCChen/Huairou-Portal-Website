from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class APIResponse(BaseModel):
    code: int = 200
    message: str = "ok"
    data: Any = None


class Pagination(BaseModel):
    items: list[Any]
    page: int
    page_size: int
    total: int


class TokenPayload(BaseModel):
    sub: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SmsLoginRequest(BaseModel):
    mobile: str
    code: str


class SmsSendRequest(BaseModel):
    mobile: str


class RegisterRequest(BaseModel):
    real_name: str
    organization: str
    mobile: str
    email: EmailStr | None = None
    expertise: str
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None
    mobile: str | None
    email: str | None
    real_name: str
    organization: str | None
    expertise: str | None
    status: str
    role_id: int
    created_at: datetime


class AuthTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ContentBase(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    content_html: str
    status: str = "draft"
    publish_at: datetime | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    seo_keywords: str | None = None


class ArticleIn(ContentBase):
    category_id: int | None = None
    source: str | None = None
    author: str | None = None
    cover_file_id: int | None = None
    is_top: bool = False
    attachments: list[int] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)


class CaseIn(ContentBase):
    partner_name: str | None = None
    stage: str | None = None
    cover_file_id: int | None = None
    highlights: list[str] = Field(default_factory=list)
    benefits: str | None = None
    result_blocks: list[dict] = Field(default_factory=list)
    tag_ids: list[int] = Field(default_factory=list)


class PageIn(BaseModel):
    title: str
    page_key: str
    content_html: str
    status: str = "published"
    seo_title: str | None = None
    seo_description: str | None = None
    seo_keywords: str | None = None
    blocks: list[dict] = Field(default_factory=list)


class BannerIn(BaseModel):
    title: str
    subtitle: str | None = None
    button_text: str | None = None
    button_url: str | None = None
    image_file_id: int | None = None
    tag: str | None = "院内新闻"
    sort_order: int = 0
    is_enabled: bool = True


class SettingIn(BaseModel):
    setting_value: Any
    group_name: str = "general"


class CategoryIn(BaseModel):
    name: str
    slug: str
    type: str
    parent_id: int | None = None
    sort_order: int = 0
    enabled: bool = True


class TagIn(BaseModel):
    name: str
    slug: str
    type: str = "content"
    color: str | None = None
    enabled: bool = True


class ReviewIn(BaseModel):
    review_comment: str | None = None


class AdminUserCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr | None = None
    mobile: str | None = Field(default=None, max_length=30)
    real_name: str = Field(min_length=1, max_length=100)
    organization: str | None = Field(default=None, max_length=255)
    expertise: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_code: str = "institute_editor"


class UserRejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class UserRoleUpdateIn(BaseModel):
    role_code: str = Field(min_length=1, max_length=50)


class ServiceRequestIn(BaseModel):
    type: str = "consultation"
    subject: str
    contact_name: str
    contact_mobile: str | None = None
    contact_email: EmailStr | None = None
    organization: str | None = None
    content: str


class ResetPasswordRequest(BaseModel):
    mobile: str
    code: str
    new_password: str = Field(min_length=8)


class PasswordResetRequestIn(BaseModel):
    email_or_username: str = Field(min_length=1, max_length=255)


class PasswordResetConfirmIn(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class DownloadResourceIn(BaseModel):
    title: str
    slug: str
    summary: str | None = None
    category_id: int | None = None
    file_id: int
    is_public: bool = True
    sort_order: int = 0


class LeaderIn(BaseModel):
    name: str
    title: str
    photo_file_id: int | None = None
    intro: str | None = None
    sort_order: int = 0
    is_visible: bool = True


class InstituteIn(BaseModel):
    name: str
    slug: str
    intro: str
    cover_file_id: int | None = None
    directions: list[dict] = Field(default_factory=list)
    contact: dict = Field(default_factory=dict)
    related_article_ids: list[int] = Field(default_factory=list)
    related_case_ids: list[int] = Field(default_factory=list)
    status: str = "hidden"
    sort_order: int = 0
