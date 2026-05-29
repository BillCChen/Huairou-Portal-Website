from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255))
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    real_name: Mapped[str] = mapped_column(String(100))
    organization: Mapped[str | None] = mapped_column(String(255))
    expertise: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    role: Mapped["Role"] = relationship(back_populates="users")
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(back_populates="user")


class PasswordResetToken(TimestampMixin, Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_ip: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    user: Mapped["User"] = relationship(back_populates="password_reset_tokens")


class RegistrationApplication(TimestampMixin, Base):
    __tablename__ = "registration_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    review_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    review_comment: Mapped[str | None] = mapped_column(Text())
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class Tag(TimestampMixin, Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(50), default="content")
    color: Mapped[str | None] = mapped_column(String(20))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class FileRecord(TimestampMixin, Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    scan_status: Mapped[str | None] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    scan_engine: Mapped[str | None] = mapped_column(String(100))
    scan_message: Mapped[str | None] = mapped_column(String(500))
    scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Article(TimestampMixin, Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(500))
    cover_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    content_html: Mapped[str] = mapped_column(Text())
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    source: Mapped[str | None] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(100))
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    is_top: Mapped[bool] = mapped_column(Boolean, default=False)
    seo_title: Mapped[str | None] = mapped_column(String(255))
    seo_description: Mapped[str | None] = mapped_column(String(500))
    seo_keywords: Mapped[str | None] = mapped_column(String(255))
    attachments: Mapped[list[int] | None] = mapped_column(JSON, default=list)


class ArticleTag(Base):
    __tablename__ = "article_tags"
    __table_args__ = (UniqueConstraint("article_id", "tag_id", name="uq_article_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))


class CaseStudy(TimestampMixin, Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(500))
    cover_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    partner_name: Mapped[str | None] = mapped_column(String(255))
    stage: Mapped[str | None] = mapped_column(String(100))
    highlights: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    benefits: Mapped[str | None] = mapped_column(Text())
    content_html: Mapped[str] = mapped_column(Text())
    result_blocks: Mapped[list[dict] | None] = mapped_column(JSON, default=list)
    publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    seo_title: Mapped[str | None] = mapped_column(String(255))
    seo_description: Mapped[str | None] = mapped_column(String(500))
    seo_keywords: Mapped[str | None] = mapped_column(String(255))


class CaseTag(Base):
    __tablename__ = "case_tags"
    __table_args__ = (UniqueConstraint("case_id", "tag_id", name="uq_case_tag"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"))


class Page(TimestampMixin, Base):
    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    content_html: Mapped[str] = mapped_column(Text())
    seo_title: Mapped[str | None] = mapped_column(String(255))
    seo_description: Mapped[str | None] = mapped_column(String(500))
    seo_keywords: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(30), default="published")
    blocks: Mapped[list[dict] | None] = mapped_column(JSON, default=list)


class Leader(TimestampMixin, Base):
    __tablename__ = "leaders"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(100))
    photo_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    intro: Mapped[str | None] = mapped_column(Text())
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)


class Institute(TimestampMixin, Base):
    __tablename__ = "institutes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    slug: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    intro: Mapped[str] = mapped_column(Text())
    cover_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    directions: Mapped[list[dict] | None] = mapped_column(JSON, default=list)
    contact: Mapped[dict | None] = mapped_column(JSON, default=dict)
    related_article_ids: Mapped[list[int] | None] = mapped_column(JSON, default=list)
    related_case_ids: Mapped[list[int] | None] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="hidden")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Banner(TimestampMixin, Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str | None] = mapped_column(String(500))
    button_text: Mapped[str | None] = mapped_column(String(100))
    button_url: Mapped[str | None] = mapped_column(String(255))
    image_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tag: Mapped[str | None] = mapped_column(String(50))


class SiteSetting(TimestampMixin, Base):
    __tablename__ = "site_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    setting_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    setting_value: Mapped[dict | list | str | int | None] = mapped_column(JSON)
    group_name: Mapped[str] = mapped_column(String(50), default="general")


class DownloadResource(TimestampMixin, Base):
    __tablename__ = "download_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(500))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id"))
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ServiceRequest(TimestampMixin, Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    subject: Mapped[str] = mapped_column(String(255))
    contact_name: Mapped[str] = mapped_column(String(100))
    contact_mobile: Mapped[str | None] = mapped_column(String(30))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    organization: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    module: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50))
    object_type: Mapped[str] = mapped_column(String(50))
    object_id: Mapped[str | None] = mapped_column(String(100))
    detail_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    path: Mapped[str | None] = mapped_column(String(255))
    method: Mapped[str | None] = mapped_column(String(10))
    result: Mapped[str | None] = mapped_column(String(30))
    failure_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginLog(Base):
    __tablename__ = "login_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    username: Mapped[str | None] = mapped_column(String(100))
    login_method: Mapped[str] = mapped_column(String(30))
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    path: Mapped[str | None] = mapped_column(String(255))
    method: Mapped[str | None] = mapped_column(String(10))
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    failure_reason: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
