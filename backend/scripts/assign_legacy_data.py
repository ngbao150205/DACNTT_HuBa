"""Explicit local admin action; no public HTTP endpoint can claim legacy data."""
import argparse
from sqlalchemy import text
from database.connection import SessionLocal
from database.models import Product, User


def assign_legacy_data(db, email):
    if db.get_bind().dialect.name == "postgresql":
        # Prevent concurrent product creation/claims while checking collisions.
        db.execute(text("LOCK TABLE products IN SHARE ROW EXCLUSIVE MODE"))
    user = db.query(User).filter_by(email=email.strip().lower(), is_active=True).first()
    if not user:
        raise ValueError("Chưa tìm thấy tài khoản. Hãy đăng ký tài khoản trước.")
    legacy = db.query(Product).filter(Product.owner_id.is_(None)).with_for_update().all()
    owned = {(p.platform, p.platform_product_id) for p in db.query(Product).filter_by(owner_id=user.id)}
    if any((p.platform, p.platform_product_id) in owned for p in legacy):
        raise ValueError("Tài khoản đã có sản phẩm trùng dữ liệu cũ. Chưa thay đổi gì; cần quản trị viên xem xét trước khi gộp.")
    for product in legacy:
        product.owner_id = user.id
    db.commit()
    return len(legacy)


def main():
    parser = argparse.ArgumentParser(description="Gán toàn bộ sản phẩm chưa có chủ cho một tài khoản; giữ nguyên review và lịch sử.")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    with SessionLocal() as db:
        try:
            count = assign_legacy_data(db, args.email)
        except ValueError as error:
            db.rollback()
            raise SystemExit(str(error))
    print(f"Đã gán {count} sản phẩm chưa có chủ. Review và lịch sử được giữ nguyên.")

if __name__ == "__main__": main()
