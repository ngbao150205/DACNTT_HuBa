# Crawler Lazada — TinyFish Agent API

`POST /crawl` nhận URL sản phẩm HTTPS Lazada Việt Nam, gọi **TinyFish Agent
API**, rồi chuẩn hóa tên sản phẩm/review cho backend. Backend tiếp tục dùng
model v3 và rule hiện có, lưu PostgreSQL. Crawler không dùng TinyFish để quyết
định sentiment.

Cấu hình trong `.env` gốc dự án:

```dotenv
TINYFISH_API_KEY=YOUR_TINYFISH_API_KEY
TINYFISH_TIMEOUT_SECONDS=600
```

Lấy khóa tại [TinyFish API Keys](https://agent.tinyfish.ai/api-keys). Giữ khóa
thật trong `.env` cục bộ; không gửi vào Git, chat, log hoặc giao diện. Không cần
Cookie, User-Agent Lazada hoặc trình duyệt chạy trong container ứng dụng.

Compose đặt `CRAWLER_ENV_FILE=/run/duancntt/config/.env` và mount thư mục gốc
read-only. Mỗi lượt crawl mới đọc lại khóa/timeout nên không cần restart khi đổi
hai giá trị này. Lượt đang chạy giữ cấu hình đã đọc. Thiếu khóa làm luồng URL
báo lỗi cấu hình; nhánh CSV/Excel không phụ thuộc TinyFish.

- Mặc định luôn dùng TinyFish, không fallback sang cookie hoặc nguồn cũ.
- Chỉ giữ review có nội dung; chuẩn hóa trường dữ liệu và loại trùng trước khi
  gửi sang backend.
- Kết quả một phần vẫn giữ review hợp lệ, trả trạng thái/cảnh báo và metadata
  về mức độ đầy đủ. Không suy ra đã lấy mọi đánh giá chỉ từ số review hoặc
  việc dịch vụ đã kết thúc lượt chạy.
- Timeout mặc định 600 giây là thời gian chờ thu thập; backend còn cần thời gian
  phân tích review sau đó.
- TinyFish là dịch vụ bên thứ ba có chi phí và hạn mức theo tài khoản. Không có
  bảo đảm lấy hết đánh giá, truy cập được mọi sản phẩm hoặc vượt CAPTCHA.
- `cookie_crawler.py` là mã legacy để tham khảo/kiểm thử offline; không nằm
  trong đường gọi URL đang hoạt động.

Khởi chạy từ thư mục gốc với `docker compose up -d`. Nếu cập nhật source/image
cũ, dùng `docker compose up -d --build crawler-service backend frontend` một lần.
Xem [hướng dẫn URL/file](../HYBRID_COLLECTION.md#2-url--tinyfish-agent-api-và-khóa-trong-env)
và [tài liệu TinyFish chính thức](https://docs.tinyfish.ai).

```bash
docker compose logs -f --tail=100 crawler-service backend
docker compose run --rm --no-deps crawler-service python -m unittest discover -s tests -v
```

Bộ test dùng dữ liệu giả lập, không kiểm chứng một lượt truy cập Lazada thật và
không tiêu thụ API TinyFish. Khi chạy thử URL thật, kiểm tra khóa, hạn mức/chi
phí và metadata của lượt thu thập; không in khóa ra terminal.
