# Crawler Lazada — luồng hiện tại

Mặc định dùng hàm do chủ dự án cung cấp, đã tích hợp tại
[cookie_crawler.py](cookie_crawler.py): `crawl_lazada_reviews(product_id, datapath,
stars=(1,2,3,4,5), max_pages=None, cookie=None)`.

Cấu hình và cách đổi cookie không cần restart: [hướng dẫn URL/file](../HYBRID_COLLECTION.md#2-url--hàm-crawl-và-cookie-trong-env).
Không cần Chrome Extension. Backend lưu PostgreSQL và dùng model/rule hiện có.

- Crawler chỉ dùng hàm cookie, không còn các chế độ browser/HTTP cũ.
- Đặt LAZADA_COOKIE trong `.env` gốc; được đọc lại mỗi lượt crawl.
- Chỉ lấy các bình luận có nội dung, phân trang đủ 5 mức sao, không giới hạn trang.
- Gặp chặn thì dừng, giữ kết quả đã lấy và trả PARTIAL; cookie không đảm bảo
  lấy được mọi đánh giá trong mọi phiên.
- Không log/trả cookie. URL phải là trang sản phẩm HTTPS Lazada Việt Nam hợp lệ.
- CSV xuất tại `/var/lib/crawler/exports` trong volume crawler_data.

```bash
docker compose logs -f --tail=100 crawler-service backend
docker compose run --rm --no-deps crawler-service python -m unittest discover -s tests -v
```
