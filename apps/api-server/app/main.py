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


def ensure_banner_tag_column():
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(banners)")).fetchall()
    has_tag = any(row[1] == "tag" for row in rows)
    if has_tag:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE banners ADD COLUMN tag VARCHAR(50)"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_banner_tag_column()
    if settings.init_sample_data:
        with SessionLocal() as session:
            seed_database(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
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
