"""Authenticated user-supplied data; never fetch Lazada or accept its cookies."""

import json
import logging

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.connection import get_db
from app.services.collection_service import (
    MAX_BYTES, MAX_ROWS, CollectionValidationError, collect_reviews, parse_file, product_identity,
)
from app.services.review_identity import ReviewIdentityConflict

logger = logging.getLogger(__name__)
from app.security.auth import get_current_user
from database.models import User

router = APIRouter(prefix="/collections", tags=["Collections"], dependencies=[Depends(get_current_user)])

@router.get("/status")
def status():
    return {"status": "ready", "max_bytes": MAX_BYTES, "max_rows": MAX_ROWS}


async def read_body(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BYTES:
            raise HTTPException(413, "Tối đa 5 MiB mỗi lần gửi; hãy chia dữ liệu thành nhiều file.")
    return bytes(body)


def process(db, **kwargs):
    try:
        return collect_reviews(db, **kwargs)
    except (CollectionValidationError, ReviewIdentityConflict) as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Dữ liệu vừa được cập nhật ở phiên khác. Hãy gửi lại để gộp và chống trùng.") from exc
    except requests.RequestException as exc:
        db.rollback()
        raise HTTPException(502, "AI service chưa xử lý được dữ liệu. Chưa lưu lần nhập này; hãy thử lại.") from exc
    except Exception as exc:
        db.rollback()
        logger.exception("Review collection failed")
        raise HTTPException(500, "Nhập dữ liệu thất bại; đã hoàn tác lần nhập này.") from exc


@router.post("/reviews")
async def collected_reviews(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    raw = await read_body(request)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError()
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise HTTPException(422, "Cần JSON object có product_url và mảng reviews.")
    return await run_in_threadpool(process, db, owner_id=user.id, product_url=data.get("product_url"),
                                   product_name=data.get("product_name"), rows=data.get("reviews"), source="api")


@router.post("/import")
async def import_reviews(request: Request, format: str, product_name: str = "", product_url: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    raw = await read_body(request)
    try:
        rows, metadata = await run_in_threadpool(parse_file, raw, format.lower())
        product_id = product_identity(product_url)[0] if product_url else None
        if product_id is not None and metadata.get("product_url") and product_identity(metadata["product_url"])[0] != product_id:
            raise CollectionValidationError("product_url trong file không khớp URL đã nhập.")
        if product_id is not None and metadata.get("product_id") is not None and str(metadata["product_id"]) != product_id:
            raise CollectionValidationError("product_id trong file không khớp URL đã nhập.")
    except CollectionValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    return await run_in_threadpool(process, db, owner_id=user.id, product_url=product_url,
                                   product_name=product_name if not product_url else product_name or metadata.get("product_name"),
                                   rows=rows, source=f"{format.lower()}_import")
