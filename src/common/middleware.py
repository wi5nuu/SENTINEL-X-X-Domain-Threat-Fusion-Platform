import time
import uuid
import re
from typing import Callable
from collections import defaultdict
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from src.common.logging import setup_logging
from src.common.config import settings

logger = setup_logging("middleware")

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_TIME_HEADER = "X-Request-Time"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return Response(
                status_code=429,
                content='{"detail":"Rate limit exceeded. Try again later."}',
                media_type="application/json",
                headers={"Retry-After": str(self.window_seconds)},
            )
        self.requests[client_ip].append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[REQUEST_TIME_HEADER] = datetime.utcnow().isoformat()
        return response


class InputValidationMiddleware(BaseHTTPMiddleware):
    SQL_INJECTION_PATTERN = re.compile(
        r"('|--|;|\/\*|\*\/|xp_|sp_|UNION\s+SELECT|SELECT\s+.*\s+FROM|DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+.*\s+SET|EXEC\s+|EXECUTE\s+|xp_cmdshell|OR\s+'1'\s*=\s*'1|OR\s+1\s*=\s*1)",
        re.IGNORECASE,
    )
    XSS_PATTERN = re.compile(
        r"(<script[^>]*>|<\/script>|javascript:|onerror=|onload=|onclick=|onmouseover=|eval\(|document\.cookie|alert\()",
        re.IGNORECASE,
    )
    PATH_TRAVERSAL_PATTERN = re.compile(r"(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e%5c|\.\..*\/)", re.IGNORECASE)

    async def dispatch(self, request: Request, call_next: Callable):
        if request.method in ("POST", "PUT", "PATCH"):
            body = await request.body()
            body_str = body.decode("utf-8", errors="ignore") if body else ""
            for pattern, name in [
                (self.SQL_INJECTION_PATTERN, "SQL injection"),
                (self.XSS_PATTERN, "XSS"),
                (self.PATH_TRAVERSAL_PATTERN, "path traversal"),
            ]:
                if pattern.search(body_str):
                    client_ip = request.client.host if request.client else "unknown"
                    logger.warning(
                        f"Blocked {name} attempt from {client_ip}",
                        extra={"path": str(request.url), "method": request.method},
                    )
                    return Response(
                        status_code=400,
                        content=f'{{"detail":"Request blocked: suspicious content detected ({name})"}}',
                        media_type="application/json",
                    )
        return await call_next(request)


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = str(request.url.path)
        start = time.time()
        response = await call_next(request)
        elapsed = time.time() - start
        logger.info(
            "API request",
            extra={
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed * 1000, 2),
                "client_ip": client_ip,
            },
        )
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {
        "/health",
        "/api/health",
        "/api/v1/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/ws",
    }

    async def dispatch(self, request: Request, call_next: Callable):
        path = str(request.url.path)
        if path in self.PUBLIC_PATHS or path.startswith(("/docs/", "/redoc/")):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or ""
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]

        if settings.sentinel_api_key and api_key == settings.sentinel_api_key:
            return await call_next(request)

        if not settings.sentinel_api_key:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        logger.warning(f"Unauthenticated access attempt from {client_ip}", extra={"path": path, "method": request.method})
        return Response(
            status_code=401,
            content='{"detail":"Authentication required. Provide X-API-Key header or Authorization: Bearer <token>."}',
            media_type="application/json",
            headers={"WWW-Authenticate": "Bearer"},
        )