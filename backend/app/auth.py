"""Authentication (Supabase JWT) + business authorization.

The business is NEVER taken from the request as proof of access: it is resolved from the
business_members table for the authenticated user. An optional X-Business-Id header only
*selects* among businesses the user already belongs to.
"""
import logging
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config
from app.db.database import get_cursor
from app.errors import AppError

log = logging.getLogger("bizflow")
_bearer = HTTPBearer(auto_error=False)
_jwks_client = None


@dataclass(frozen=True)
class CurrentUser:
    id: str


def _unauthenticated() -> AppError:
    return AppError(401, "unauthenticated", "Authentication required.")


def _signing_key(token: str):
    global _jwks_client
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        if not config.SUPABASE_JWT_SECRET:
            raise RuntimeError("SUPABASE_JWT_SECRET not configured")
        return config.SUPABASE_JWT_SECRET, ["HS256"]
    if alg in ("ES256", "RS256") and config.SUPABASE_URL:
        if _jwks_client is None:
            _jwks_client = jwt.PyJWKClient(f"{config.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json")
        return _jwks_client.get_signing_key_from_jwt(token).key, [alg]
    raise jwt.InvalidAlgorithmError("unsupported algorithm")


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthenticated()
    try:
        key, algs = _signing_key(creds.credentials)
        claims = jwt.decode(creds.credentials, key, algorithms=algs, audience=config.JWT_AUDIENCE,
                            options={"require": ["exp", "sub"]})
        return CurrentUser(id=str(uuid.UUID(claims["sub"])))
    except (jwt.PyJWTError, ValueError):
        raise _unauthenticated()
    except RuntimeError:
        log.error("auth misconfigured: signing secret missing")
        raise AppError(500, "auth_misconfigured", "Authentication is not configured.")


def get_business_id(user: CurrentUser = Depends(get_current_user),
                    x_business_id: str | None = Header(default=None)) -> str:
    with get_cursor() as cur:
        cur.execute("SELECT business_id FROM business_members WHERE user_id = %s ORDER BY created_at", (user.id,))
        owned = [str(r["business_id"]) for r in cur.fetchall()]
    if not owned:
        raise AppError(403, "no_business_access", "You do not have access to any business.")
    if x_business_id:
        try:
            wanted = str(uuid.UUID(x_business_id))
        except ValueError:
            raise AppError(400, "invalid_business_id", "Invalid business identifier.")
        if wanted not in owned:
            raise AppError(403, "forbidden_business", "You do not have access to this business.")
        return wanted
    if len(owned) > 1:
        raise AppError(400, "business_required", "Multiple businesses found; send the X-Business-Id header.")
    return owned[0]
