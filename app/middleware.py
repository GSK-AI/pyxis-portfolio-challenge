import logging
import os
from typing import Dict, Tuple

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.settings import settings

logger = logging.getLogger(__name__)


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


class NoCredentialsError(Exception):
    """Raised when no credential headers are provided."""

    pass


class UserFromJWTAuthMiddleware(BaseHTTPMiddleware):
    """Get logged user info from JWT token."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        For each request, get the user details from JWT and then pass the request on.

        Parameters
        ----------
        request
            HTTP request object from Starlette

        call_next
            Path definition function to be called next

        Returns
        -------
        Response
            HTTP response after path definition function has executed

        """
        # Skip middleware if running in test mode or if it's an OPTIONS request
        if os.getenv("TESTING", "0") == "1" or request.method == "OPTIONS":
            return await call_next(request)
        logger.info(f"Request path: {request.url.path}, method: {request.method}")
        if request.url.path not in settings.auth_excluded_routes:
            headers = request.headers
            try:
                email, mudid, name, session_id, roles = self.extract_auth_headers(
                    headers
                )
            except NoCredentialsError:
                return Response(status_code=401)

            request.state.mudid = mudid
            request.state.name = name
            request.state.email = email
            request.state.session_id = session_id

            logger.info(f"These are the group memberships: {roles}")
            logger.info(f"This is the user: {name}")

            if "all" in roles:
                request.state.access = [
                    "all",
                    "oncology",
                    "vaccines",
                    "respiratory_immunology",
                ]
            elif "oncology" in roles:
                request.state.access = ["oncology"]
            elif "vaccines" in roles:
                request.state.access = ["vaccines"]
            elif "respiratory_immunology" in roles:
                request.state.access = ["respiratory_immunology"]
            else:
                request.state.access = ["dummy"]

        response = await call_next(request)
        return response

    @classmethod
    def extract_auth_headers(cls, headers) -> Tuple[str, str, str, str, list[str]]:
        """Get email, mudid, name, country from FastAPI headers containing auth info."""
        match headers:
            # add more cases for other keys in headers
            case {"authorization": auth_header}:
                logger.debug("Looking in Authorization header for user info")
                decoded_jwt = cls._process_bearer_id_header(auth_header)
            case _:
                raise NoCredentialsError("No auth headers provided")
        email = decoded_jwt["email"]
        mudid = decoded_jwt["email"].split("@")[0]
        name = decoded_jwt["name"]
        session_id = decoded_jwt["sid"]
        # Extract security group information from the token
        roles = decoded_jwt.get("roles", [])
        return email, mudid, name, session_id, roles

    @staticmethod
    def _process_bearer_id_header(auth_header: str) -> Dict[str, str]:
        auth_type, token = auth_header.split(" ", 1)
        if not auth_type.lower() == "bearer":
            raise ValueError("Authorisation uses an unsupported auth type")

        # these are app environment variables
        tenant_id = os.environ.get("AZURE_TENANT_ID")
        client_id = os.environ.get("AZURE_CLIENT_ID")
        if not tenant_id or not client_id:
            logger.error(
                "Missing AZURE_TENANT_ID or AZURE_CLIENT_ID environment variables"
            )
            raise ValueError("Azure configuration is incomplete")

        options = {"verify_signature": True, "verify_aud": True, "verify_exp": True}
        try:
            # Azure AD tokens should be verified with their public keys
            # This approach uses the PyJWT library with auto-fetching of keys
            jwks_client = jwt.PyJWKClient(
                f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
            )
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            decoded_jwt = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=client_id,
                options=options,
            )
            logger.debug(f"Token decoded successfully: {decoded_jwt}")
            return decoded_jwt
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise ValueError("Invalid token")
