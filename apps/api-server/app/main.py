from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router
from app.core.config import settings
from app.db.seed import seed_database
from app.schemas import APIResponse
from app.db.session import Base, SessionLocal, engine
from app.services.request_context import extract_request_meta, reset_current_request_meta, set_current_request_meta


def ensure_sqlite_columns(table_name: str, columns: dict[str, str]) -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    existing = {row[1] for row in rows}
    missing = {name: definition for name, definition in columns.items() if name not in existing}
    if not missing:
        return
    with engine.begin() as conn:
        for name, definition in missing.items():
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {name} {definition}"))


def ensure_sqlite_schema_compatibility():
    ensure_sqlite_columns("banners", {"tag": "VARCHAR(50)"})
    ensure_sqlite_columns(
        "audit_logs",
        {
            "ip_address": "VARCHAR(50)",
            "user_agent": "VARCHAR(512)",
            "path": "VARCHAR(255)",
            "method": "VARCHAR(10)",
            "result": "VARCHAR(30)",
            "failure_reason": "VARCHAR(100)",
        },
    )
    ensure_sqlite_columns(
        "login_logs",
        {
            "user_agent": "VARCHAR(512)",
            "path": "VARCHAR(255)",
            "method": "VARCHAR(10)",
            "failure_reason": "VARCHAR(100)",
        },
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema_compatibility()
    if settings.init_sample_data:
        with SessionLocal() as session:
            seed_database(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    token = set_current_request_meta(extract_request_meta(request))
    try:
        return await call_next(request)
    finally:
        reset_current_request_meta(token)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)
app.include_router(router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(
            code=exc.status_code,
            message=str(exc.detail),
            data=None,
        ).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    first_error = exc.errors()[0] if exc.errors() else {}
    message = first_error.get("msg", "Validation error")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            data=None,
        ).model_dump(),
    )
