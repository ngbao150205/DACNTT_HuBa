import hashlib
import math
import secrets
from datetime import timedelta
from sqlalchemy import case, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from fastapi import HTTPException
from pwdlib import PasswordHash
from database.models import AuthSession, AuthThrottle, UserApiToken
from app.security.auth import SESSION_SECONDS, token_hash, utcnow

passwords = PasswordHash.recommended()
# Perform the same password verification for unknown users.
DUMMY_HASH = passwords.hash(secrets.token_urlsafe(24))


def public_user(user):
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


def rate_limit(db, scope, identifier, *, limit, seconds):
    now = utcnow()
    key = hashlib.sha256(f"{scope}:{identifier}".encode()).hexdigest()
    table = AuthThrottle.__table__
    insert = pg_insert if db.get_bind().dialect.name == "postgresql" else sqlite_insert
    expired = table.c.window_start <= now - timedelta(seconds=seconds)
    statement = insert(table).values(key=key, window_start=now, attempts=1)
    statement = statement.on_conflict_do_update(index_elements=["key"], set_={
        "window_start": case((expired, now), else_=table.c.window_start),
        "attempts": case((expired, 1), else_=table.c.attempts + 1),
    }).returning(table.c.attempts, table.c.window_start)
    attempts, started = db.execute(statement).one()
    db.commit()  # Failed sign-ins must not roll back their throttle counter.
    if attempts > limit:
        retry = max(1, math.ceil(seconds - (now - started).total_seconds()))
        raise HTTPException(429, "Bạn thao tác quá nhiều lần. Vui lòng thử lại sau.", headers={"Retry-After": str(retry)})


def create_session(db, user):
    raw = secrets.token_urlsafe(32)
    db.add(AuthSession(user_id=user.id, token_hash=token_hash(raw),
                       expires_at=utcnow() + timedelta(seconds=SESSION_SECONDS)))
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= utcnow()))
    return raw


def revoke_credentials(db, user_id):
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    db.execute(delete(UserApiToken).where(UserApiToken.user_id == user_id))
