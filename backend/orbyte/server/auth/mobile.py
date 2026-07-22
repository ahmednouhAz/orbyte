"""Mobile auth gateway.

Native mobile clients (Expo / React Native) authenticate against the SAME
backend as web, but receive the existing stateful session token as a Bearer
value instead of an HttpOnly cookie. This module owns the mobile-facing auth
surface.

Endpoints:
  - POST /auth/mobile/login         email/password -> {access_token, token_type}
  - POST /auth/mobile/logout        revoke the current session token
  - POST /auth/mobile/refresh       extend / reissue the session token

NOTE: SSO (Google OAuth / OIDC / SAML) has been removed from this deployment,
so the mobile SSO code-exchange bridge that used to live here has been
removed as well — Basic (local email/password) auth only.
"""

from fastapi import APIRouter

from orbyte.auth.users import fastapi_users
from orbyte.auth.users import mobile_auth_backend

# Prefix ("/auth/mobile") is applied at registration in main.py. The bearer
# login/refresh/logout sub-routers are built from `mobile_auth_backend`, so they
# reuse the existing session strategy — the Bearer token is the exact same token
# web gets (server-revocable under the redis/postgres backends); only the
# transport differs. Their route names are namespaced `auth:mobile-bearer.*`, so
# they never collide with the web cookie backend's `auth:<backend>.*` routes.
router = APIRouter()
# get_auth_router provides both /login and /logout for the bearer backend.
router.include_router(fastapi_users.get_auth_router(mobile_auth_backend))
router.include_router(fastapi_users.get_refresh_router(mobile_auth_backend))
