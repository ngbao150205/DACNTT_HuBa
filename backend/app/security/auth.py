"""Revocable opaque sessions and personal API keys, stored as hashes only."""
import hashlib
import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from database.connection import get_db
from database.models import AuthSession, User, UserApiToken

bearer = HTTPBearer(auto_error=False)
COOKIE_NAME = "duancntt_session"
SESSION_SECONDS = 7 * 24 * 60 * 60


def utcnow():
    return datetime.utcnow()


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def allowed_origins():
    return {os.getenv("AUTH_FRONTEND_URL", "http://localhost:5173").rstrip("/"),
            "http://localhost:5173", "http://127.0.0.1:5173"}


def check_origin(request: Request):
    # Browser POSTs send Origin. Non-browser clients must still authenticate.
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and origin not in allowed_origins():
            raise HTTPException(403, "Nguồn yêu cầu không được phép.")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Yêu cầu từ trang ngoài không được phép.")


def unauthorized():
    return HTTPException(401, "Vui lòng đăng nhập hoặc dùng khóa API cá nhân hợp lệ.",
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db=Depends(get_db)):
    if credentials is not None:
        token = db.query(UserApiToken).filter(
            UserApiToken.token_hash == token_hash(credentials.credentials),
            UserApiToken.expires_at > utcnow(),
        ).first() if credentials.scheme.lower() == "bearer" else None
    else:
        value = request.cookies.get(COOKIE_NAME)
        token = db.query(AuthSession).filter(
            AuthSession.token_hash == token_hash(value), AuthSession.expires_at > utcnow(),
        ).first() if value and len(value) <= 200 else None
        check_origin(request)
    user = db.get(User, token.user_id) if token else None
    if not user or not user.is_active:
        raise unauthorized()
    return user


def get_session_user(request: Request, db=Depends(get_db)):
    # Account settings cannot be accessed using an personal API key.
    value = request.cookies.get(COOKIE_NAME)
    session = db.query(AuthSession).filter(
        AuthSession.token_hash == token_hash(value), AuthSession.expires_at > utcnow(),
    ).first() if value and len(value) <= 200 else None
    check_origin(request)
    user = db.get(User, session.user_id) if session else None
    if not user or not user.is_active:
        raise unauthorized()
    return user


def set_session_cookie(response, raw):
    secure = os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true"
    response.set_cookie(COOKIE_NAME, raw, max_age=SESSION_SECONDS, httponly=True,
                        secure=secure, samesite="lax", path="/")
