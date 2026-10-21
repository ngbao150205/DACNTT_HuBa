import os
import secrets
from datetime import timedelta
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from database.connection import get_db
from database.models import AuthSession, PasswordResetToken, User, UserApiToken
from app.schemas.auth import EmailRequest, LoginRequest, RegisterRequest, ResetPasswordRequest
from app.security.auth import COOKIE_NAME, check_origin, get_current_user, get_session_user, set_session_cookie, token_hash, utcnow
from app.services.auth_mail import send_reset_email
from app.services.auth_service import DUMMY_HASH, create_session, passwords, public_user, rate_limit, revoke_credentials

router = APIRouter(prefix="/auth", tags=["Authentication"])


def client_ip(request):
    # Do not trust arbitrary X-Forwarded-For from the caller.
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=201)
def register(data: RegisterRequest, request: Request, response: Response, db=Depends(get_db)):
    check_origin(request)
    rate_limit(db, "register-ip", client_ip(request), limit=10, seconds=3600)
    user = User(email=str(data.email), full_name=data.full_name, password_hash=passwords.hash(data.password))
    try:
        db.add(user)
        db.flush()
        raw = create_session(db, user)
        result = public_user(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email không thể đăng ký. Hãy đăng nhập hoặc dùng chức năng quên mật khẩu.")
    set_session_cookie(response, raw)
    return {"user": result}


@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response, db=Depends(get_db)):
    check_origin(request)
    rate_limit(db, "login-ip", client_ip(request), limit=30, seconds=300)
    rate_limit(db, "login-email", str(data.email), limit=10, seconds=300)
    user = db.query(User).filter_by(email=str(data.email)).with_for_update().first()
    valid = passwords.verify(data.password, user.password_hash if user else DUMMY_HASH)
    if not valid or not user or not user.is_active:
        raise HTTPException(401, "Email hoặc mật khẩu không đúng.")
    raw = create_session(db, user)
    result = public_user(user)
    db.commit()
    set_session_cookie(response, raw)
    return {"user": result}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return {"user": public_user(user)}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db=Depends(get_db)):
    check_origin(request)
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(raw)))
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="lax",
                           secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true")


@router.post("/forgot-password", status_code=202)
def forgot_password(data: EmailRequest, request: Request, tasks: BackgroundTasks, db=Depends(get_db)):
    check_origin(request)
    rate_limit(db, "forgot-ip", client_ip(request), limit=10, seconds=900)
    rate_limit(db, "forgot-email", str(data.email), limit=3, seconds=900)
    user = db.query(User).filter_by(email=str(data.email), is_active=True).with_for_update().first()
    if user:
        raw = secrets.token_urlsafe(32)
        db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash(raw), expires_at=utcnow() + timedelta(minutes=15)))
        address, name = user.email, user.full_name
        db.commit()
        # Fragment keeps the raw token out of HTTP request URLs and referrers.
        base = os.getenv("AUTH_FRONTEND_URL", "http://localhost:5173").rstrip("/")
        tasks.add_task(send_reset_email, address, name, f"{base}/reset-password#{urlencode({'token': raw})}")
    return {"message": "Nếu email đã được đăng ký, bạn sẽ nhận được liên kết đặt lại mật khẩu."}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, request: Request, db=Depends(get_db)):
    check_origin(request)
    rate_limit(db, "reset-ip", client_ip(request), limit=20, seconds=900)
    user_id = db.query(PasswordResetToken.user_id).filter_by(token_hash=token_hash(data.token)).scalar()
    if user_id is None:
        raise HTTPException(400, "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.")
    # User first, then reset token: same lock order as forgot-password/key rotation.
    user = db.query(User).filter_by(id=user_id, is_active=True).with_for_update().first()
    if not user:
        raise HTTPException(400, "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.")
    reset = db.query(PasswordResetToken).filter_by(token_hash=token_hash(data.token)).with_for_update().first()
    if not reset or reset.used_at or reset.expires_at <= utcnow():
        raise HTTPException(400, "Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.")
    user.password_hash = passwords.hash(data.password)
    reset.used_at = utcnow()
    revoke_credentials(db, user.id)
    db.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id, PasswordResetToken.id != reset.id))
    db.commit()
    return {"message": "Đã đặt lại mật khẩu. Vui lòng đăng nhập bằng mật khẩu mới."}


@router.post("/api-token")
def create_api_token(request: Request, user=Depends(get_session_user), db=Depends(get_db)):
    # Serializes key rotation for the same account.
    db.query(User).filter_by(id=user.id).with_for_update().one()
    get_session_user(request, db)  # Recheck after waiting for a concurrent password reset.
    db.execute(delete(UserApiToken).where(UserApiToken.user_id == user.id))
    raw = secrets.token_urlsafe(32)
    expires = utcnow() + timedelta(days=90)
    db.add(UserApiToken(user_id=user.id, token_hash=token_hash(raw), expires_at=expires))
    db.commit()
    return {"token": raw, "expires_at": expires.isoformat() + "Z"}


@router.delete("/api-token", status_code=204)
def revoke_api_token(request: Request, user=Depends(get_session_user), db=Depends(get_db)):
    db.query(User).filter_by(id=user.id).with_for_update().one()
    get_session_user(request, db)  # Recheck after waiting for a concurrent password reset.
    db.execute(delete(UserApiToken).where(UserApiToken.user_id == user.id))
    db.commit()
