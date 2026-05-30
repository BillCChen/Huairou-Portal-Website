from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

from fastapi import Request

from app.core.config import settings


MAX_USER_AGENT_LENGTH = 512
UNKNOWN_CLIENT_IP = "unknown"


@dataclass(frozen=True)
class RequestMeta:
    ip_address: str | None = None
    user_agent: str | None = None
    path: str | None = None
    method: str | None = None

    def as_log_fields(self) -> dict[str, str | None]:
        return {
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "path": self.path,
            "method": self.method,
        }


_current_request_meta: ContextVar[RequestMeta | None] = ContextVar("current_request_meta", default=None)


def _first_forwarded_ip(value: str | None) -> str | None:
    if not value:
        return None
    for part in value.split(","):
        candidate = part.strip()
        if candidate:
            return candidate
    return None


def get_client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded_for = _first_forwarded_ip(request.headers.get("x-forwarded-for"))
        if forwarded_for:
            return forwarded_for

        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host.strip() or UNKNOWN_CLIENT_IP

    return UNKNOWN_CLIENT_IP


def get_user_agent(request: Request) -> str | None:
    value = request.headers.get("user-agent")
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:MAX_USER_AGENT_LENGTH]


def get_request_path(request: Request) -> str:
    return request.url.path[:255]


def get_request_method(request: Request) -> str:
    return request.method.upper()[:10]


def extract_request_meta(request: Request) -> RequestMeta:
    return RequestMeta(
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        path=get_request_path(request),
        method=get_request_method(request),
    )


def set_current_request_meta(meta: RequestMeta) -> Token[RequestMeta | None]:
    return _current_request_meta.set(meta)


def reset_current_request_meta(token: Token[RequestMeta | None]) -> None:
    _current_request_meta.reset(token)


def current_request_meta() -> RequestMeta:
    return _current_request_meta.get() or RequestMeta()
