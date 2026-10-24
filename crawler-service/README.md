# Crawler Lazada — cookie trong .env

`POST /crawl` nhận URL sản phẩm Lazada Việt Nam và gọi API đánh giá bằng
`cookie_crawler.py`. Backend tiếp tục phân tích bằng model v3/rule và lưu
PostgreSQL. Luồng này không gọi TinyFish.

## Cấu hình

Chỉ cần một biến trong `.env` ở thư mục gốc dự án:

```dotenv
LAZADA_COOKIE=''
```

Điền giá trị thật giữa hai dấu nháy đơn. Không cần `LAZADA_USER_AGENT`;
`curl_cffi` tự cung cấp User-Agent mặc định.

1. Mở sản phẩm Lazada trên Chrome, mở DevTools → **Network**.
2. Mở phần đánh giá hoặc chuyển trang đánh giá, tìm request `getReviewList`.
3. Kiểm tra **Response** trả JSON có danh sách đánh giá, thay vì HTML xác minh.
4. Trong **Headers → Request Headers**, sao chép **giá trị** của `Cookie`.
5. Dán giá trị vào `LAZADA_COOKIE='...'` trong `.env`, giữ toàn bộ trên một dòng.
   Không dán chữ `Cookie:`, lệnh cURL hoặc dùng dấu backtick.

Giữ cookie thật trong `.env` cục bộ; không đưa vào Git, chat hoặc log.
Cookie phiên Lazada khác với cookie đăng nhập website DuanCNTT.

Từ thư mục gốc, khởi chạy bằng `docker compose up -d`. Nếu container đang chạy
bản TinyFish hoặc source cũ, đồng bộ một lần bằng:

```bash
docker compose up -d --build crawler-service backend frontend
```

Compose đặt `LAZADA_ENV_FILE=/run/duancntt/config/.env` và mount thư mục gốc
read-only. Mỗi lượt crawl mới đọc lại cookie, kể cả khi IDE lưu bằng atomic
rename. Những lần thay cookie tiếp theo không cần restart hoặc build lại.

## Luồng và giới hạn

- Thu thập các mức 1–5 sao, phân trang đến khi hết dữ liệu; không giới hạn 50 review.
- Chỉ giữ bình luận có nội dung, chuẩn hóa ngày và loại review trùng.
- Một HTTP session được giữ trong lượt crawl để nhận cookie cập nhật từ nguồn.
- Thiếu cookie: trả `503` trước khi gọi Lazada.
- Gặp HTML xác minh hoặc lỗi truy cập: dừng crawl, giữ các review đã lấy với
  `crawl_status=PARTIAL`. Nếu chưa lấy được review nào, trả lỗi cho backend.
- Cookie hợp lệ không bảo đảm truy cập được mọi trang đánh giá. Crawler không
  tự vượt CAPTCHA; kết quả/lịch sử đã lưu được giữ nguyên khi nguồn bị chặn.
- Nhánh nhập CSV/Excel không cần cookie.

## Kiểm tra

```bash
curl -fsS http://127.0.0.1:8002/
docker compose exec -T crawler-service python -m unittest discover -s tests -p test_cookie_crawler.py -v
docker compose logs -f --tail=100 crawler-service backend
```

Health API phải trả `crawler_mode="cookie"`, `access_mode="configured_cookie"`.
Test dùng HTTP giả lập và localhost, không gọi Lazada hoặc dùng cookie thật.
Xem thêm [hướng dẫn URL/file](../HYBRID_COLLECTION.md#2-url--cookie-trong-env).
