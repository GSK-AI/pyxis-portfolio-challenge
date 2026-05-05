import logging
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.settings import settings

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "pyxis_session"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Adds security headers to the response of a request."""
        response = await call_next(request)

        # Add security headers
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["X-Powered-By"] = "Pyxis, GSK AIML"

        # Check if it's a docs endpoint
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            # More permissive CSP for docs
            csp_policy = (
                f"default-src 'self' {settings.docs_cdn} {settings.docs_api}; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' "
                f"{settings.docs_cdn} {settings.docs_api}; "
                f"style-src 'self' 'unsafe-inline'"
                f" {settings.docs_cdn} {settings.docs_api}; "
                f"img-src 'self' data: {settings.docs_cdn} {settings.docs_api}; "
                f"font-src 'self' {settings.docs_cdn}; "
                # Also allow API connections for Swagger to work properly
                f"connect-src 'self' {settings.docs_cdn} {settings.docs_api} "
                f"{settings.dev_url} {settings.uat_url}"
                f" {settings.prod_url} {settings.main_url};"
            )
        else:
            # Strict CSP for other endpoints
            csp_policy = (
                f"default-src 'self' {settings.dev_url} {settings.uat_url}"
                f" {settings.prod_url} {settings.main_url}; "
                f"script-src 'self' {settings.dev_url} {settings.uat_url}"
                f" {settings.prod_url} {settings.main_url}; "
                f"style-src 'self' 'unsafe-inline'; "
                f"connect-src 'self' http://localhost:3000 "
                f"{settings.dev_url} {settings.uat_url}"
                f" {settings.prod_url} {settings.main_url}; "
                f"img-src 'self' data:; "
                f"font-src 'self'; "
                "frame-ancestors 'none'; "
                "object-src 'none'; "
                "base-uri 'self';"
                "report-to csp-endpoint;"
            )

        # Set Content Security Policy in enforcement mode
        response.headers["Content-Security-Policy"] = csp_policy

        return response


class SessionMiddleware(BaseHTTPMiddleware):
    """Assign each visitor a session ID via a cookie."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Read or create a session cookie, then set request.state.session_id."""
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if not session_id:
            session_id = str(uuid.uuid4())

        request.state.session_id = session_id

        response = await call_next(request)

        # Always set/refresh the cookie
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 30,  # 30 days
        )

        return response
