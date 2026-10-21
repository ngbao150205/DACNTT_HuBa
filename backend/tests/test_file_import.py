"""File-only products: CSV/Excel, name merging, isolation and rollback."""
import io
from pathlib import Path
import unittest
from urllib.parse import urlencode
from openpyxl import Workbook
import test_collections as collection_tests
from database.models import Product, Review, ReviewCollection, User, UserApiToken
from app.security.auth import token_hash, utcnow
from app.services.file_parser import CollectionValidationError, parse_file
from datetime import timedelta


def xlsx(rows):
    book = Workbook(); sheet = book.active
    for row in rows: sheet.append(row)
    buffer = io.BytesIO(); book.save(buffer); book.close()
    return buffer.getvalue()


class FileImportTests(unittest.TestCase):
    setUp = collection_tests.CollectionTests.setUp
    tearDown = collection_tests.CollectionTests.tearDown
    request = collection_tests.CollectionTests.request

    def upload(self, raw, name="Tai nghe ABC", format="csv", **kwargs):
        return self.request("/collections/import", body=raw, query=urlencode({"product_name": name, "format": format}), **kwargs)

    def test_csv_name_only_creates_import_product_and_repeated_files_merge(self):
        raw = 'Nội dung,Số sao,Người mua\nHàng tốt,5,An\n,4,Bình\n'.encode()
        for name, inserted in [("Tai nghe ABC", 1), ("  TAI  NGHE abc ", 0)]:
            status, data = self.upload(raw, name)
            self.assertEqual(status, 200, data)
            self.assertEqual(data["collection"]["inserted"], inserted)
            self.assertEqual(data["collection"]["blank"], 1)
            self.assertEqual(data["platform"], "import")
        product = self.db.query(Product).one()
        self.assertEqual(product.url, "")
        self.assertEqual(product.owner_id, self.owner_id)
        self.assertEqual(self.db.query(Review).one().platform, "import")
        self.assertEqual(self.predict.call_count, 1)
        self.assertEqual(self.db.query(ReviewCollection).count(), 2)

    def test_excel_real_workbook_handles_vietnamese_headers_and_dates(self):
        from datetime import datetime
        raw = xlsx([["review_id", "Bình luận", "Số sao", "Ngày đánh giá"], ["001", "Sản phẩm tốt", 5, datetime(2026,10,21)]])
        status, data = self.upload(raw, format="xlsx")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["collection"]["inserted"], 1)
        row = self.db.query(Review).one()
        self.assertEqual(row.platform_review_id, "001")
        self.assertEqual(row.review_date, datetime(2026,10,21))

    def test_xls_real_workbook(self):
        raw = (Path(__file__).parent / "fixtures/reviews.xls").read_bytes()
        status, data = self.upload(raw, format="xls")
        self.assertEqual(status, 200, data)
        self.assertEqual(self.db.query(Review).count(), 1)
        self.assertEqual(self.db.query(Review).one().content, "Sản phẩm tốt")

    def test_same_review_id_different_file_products_do_not_collide(self):
        raw = b'review_id,content,rating\n1,Good product,5\n'
        for name in ["Product A", "Product B"]:
            self.assertEqual(self.upload(raw, name)[0], 200)
        self.assertEqual(self.db.query(Product).count(), 2)
        self.assertEqual(self.db.query(Review).count(), 2)

    def test_each_account_has_its_own_same_name_import(self):
        raw = b'content\nGood product\n'
        first = self.upload(raw)[1]["product_db_id"]
        user = User(email="other-import@example.com", full_name="Other", password_hash="unused")
        self.db.add(user); self.db.flush()
        self.db.add(UserApiToken(user_id=user.id, token_hash=token_hash("other-personal-key"), expires_at=utcnow()+timedelta(days=1)))
        self.db.commit()
        status, data = self.upload(raw, key="other-personal-key")
        self.assertEqual(status, 200, data)
        self.assertNotEqual(first, data["product_db_id"])
        self.assertEqual(self.request(f"/products/{first}/reviews", method="GET", key="other-personal-key")[0], 404)

    def test_missing_name_invalid_excel_and_formula_never_call_ai(self):
        for name in ["", "   "]:
            self.assertEqual(self.upload(b'content\nGood\n', name)[0], 422)
        for raw in [b"not-an-xlsx", xlsx([["content"], ['=HYPERLINK("https://example.com","test")']]), xlsx([["name"], ["No content"]])]:
            self.assertEqual(self.upload(raw, format="xlsx")[0], 422)
        self.assertEqual(self.predict.call_count, 0)
        self.assertEqual(self.db.query(Product).count(), 0)

    def test_excel_limit_and_untrusted_numeric_ids(self):
        for rows in [[["review_id", "content"], [2**54, "Good"]], [["content"]] + [["Good"]] * 10001]:
            with self.assertRaises(CollectionValidationError): parse_file(xlsx(rows), "xlsx")

if __name__ == "__main__": unittest.main()
