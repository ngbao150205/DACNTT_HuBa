# Thu thập và phân tích: URL hoặc file CSV/Excel

Trang Phân tích có đúng hai lựa chọn. Cả hai dùng PostgreSQL, model
`underthesea_bilstm_custom_vocab_v3` và rule backend hiện có: confidence >= 0.8
chọn model; thấp hơn mới xét rule. Mọi dữ liệu được tách theo tài khoản.
Chrome Extension không còn nằm trong luồng sử dụng.

## 1. Tải file — chỉ tên sản phẩm và file

1. Đăng nhập website, mở **Bắt đầu phân tích → Tải file CSV / Excel**.
2. Nhập **Tên sản phẩm** và chọn file `.csv`, `.xlsx` hoặc `.xls`.
3. Bấm **Tải file và phân tích**, sau đó **Xem kết quả phân tích**.

Không cần URL, cookie hoặc khóa API. Excel đọc sheet đầu tiên, dòng đầu là tiêu
đề. CSV cần UTF-8, nhận BOM và dấu phân cách phẩy/chấm phẩy/tab.

| Cột | Bắt buộc | Tên tương đương |
| --- | --- | --- |
| `content` | Có | Nội dung, Bình luận, Đánh giá, Nhận xét, Review, text, reviewContent |
| `rating` | Không | Số sao, sao, stars; giá trị nguyên 1–5 |
| `customer_name` | Không | Người mua, Tên khách hàng, buyerName, Buyer_Name |
| `created_at` | Không | Ngày đánh giá, Date, reviewTime, review_date |
| `review_id` | Không | Mã đánh giá, reviewId, reviewRateId, reviewRelId, id |

Ví dụ: [CSV mẫu](examples/reviews.csv). Có nút tải mẫu CSV ngay trên website.
Cột `title`, `thank_count` trong file từ hàm crawl có thể giữ nguyên; pipeline
chỉ phân tích nội dung bình luận. Không dùng nhãn sentiment trong file làm kết
quả AI. Không cần cột URL hoặc ID sản phẩm.

- File tối đa 5 MiB, 10.000 dòng, 100 cột; có thể tải nhiều lần để gộp dữ liệu.
- Cùng tên sản phẩm trong cùng tài khoản được gộp, bỏ qua khoảng trắng dư và
  khác biệt chữ hoa/thường. Tên khác tạo sản phẩm khác.
- Review trùng được chống trùng theo ID gốc hoặc nội dung/tên khách/số sao.
- File không có URL được lưu `platform=import`, URL trống và ID nội bộ theo tên;
  không tạo URL Lazada giả. Dữ liệu file không tự gộp vào sản phẩm lấy từ URL,
  vì chỉ tên sản phẩm không đủ xác định chắc chắn cùng một listing Lazada.
- Review trống bị bỏ qua; emoji không đủ văn bản vẫn được lưu nhưng không gán
  cảm xúc giả. Dữ liệu lỗi làm từ chối cả lần nhập trước khi lưu.
- Excel dùng giá trị cố định. Với ô công thức, dùng Paste Special → Values.
  Lưu `review_id` dài dưới dạng Text để Excel không làm tròn mất chữ số.
- Ngày nhận ISO, dd/mm/yyyy, Unix timestamp hoặc ô ngày Excel; không biết thì
  để trống. Sheet khác sheet đầu tiên không được nhập tự động.

## 2. URL — TinyFish Agent API và khóa trong .env

Luồng mặc định: website → backend → crawler-service → **TinyFish Agent API**
→ review đã chuẩn hóa → AI/rule backend hiện có → PostgreSQL. Không cần
Cookie hoặc User-Agent Lazada, Chrome Extension hay n8n. TinyFish chỉ thu thập
và trích xuất dữ liệu; kết quả cảm xúc vẫn do model v3 và rule của hệ thống quyết định.

1. Lấy khóa tại [TinyFish API Keys](https://agent.tinyfish.ai/api-keys).
2. Nếu chưa có `.env`, chạy `cp .env.example .env` ở thư mục gốc dự án.
3. Mở `.env` cục bộ và điền khóa thật vào `TINYFISH_API_KEY`:

```dotenv
TINYFISH_API_KEY=YOUR_TINYFISH_API_KEY
TINYFISH_TIMEOUT_SECONDS=600
```

4. Chạy `docker compose up -d`, đăng nhập website và nhập URL sản phẩm Lazada Việt Nam.

Giữ khóa thật trong `.env` trên máy chạy; không đưa vào Git, chat, ảnh chụp,
log hoặc form phân tích. Backend không yêu cầu người dùng nhập khóa trên giao diện.
Thiếu khóa thì luồng URL báo lỗi cấu hình; nhập CSV/Excel vẫn hoạt động mà không cần khóa.

Nếu cập nhật từ bản cũ, build và áp dụng source mới một lần:

```bash
docker compose up -d --build backend frontend crawler-service
```

Compose mount thư mục dự án read-only tại `/run/duancntt/config` và đặt
`CRAWLER_ENV_FILE=/run/duancntt/config/.env`. Crawler đọc lại
`TINYFISH_API_KEY` và `TINYFISH_TIMEOUT_SECONDS` từ `.env` **mỗi lần bắt đầu
crawl mới**, kể cả khi IDE lưu file bằng atomic rename. Đổi hai giá trị này
không cần restart hoặc build; lượt đang chạy dùng cấu hình đã đọc lúc bắt đầu.
Những cấu hình service khác vẫn cần recreate container khi thay đổi.

`TINYFISH_TIMEOUT_SECONDS` mặc định 600 giây, giới hạn thời gian crawler chờ
lượt thu thập TinyFish. Đây không phải cam kết thời gian hoàn tất toàn bộ phân tích:
backend còn chạy AI/rule cho review mới. URL sản phẩm được gửi đến dịch vụ
TinyFish bên thứ ba; các biến database/SMTP không nằm trong yêu cầu thu thập.
TinyFish có chi phí và hạn mức theo tài khoản, nên kiểm tra tài khoản trước khi
chạy nhiều lượt. Xem [tài liệu TinyFish chính thức](https://docs.tinyfish.ai).

Crawler yêu cầu lấy các đánh giá có nội dung, chuẩn hóa dữ liệu và bỏ review
rỗng/trùng. Khi có kết quả một phần, hệ thống giữ review hợp lệ đã lấy, phân tích
và lưu chúng, kèm `crawl_status`, `crawl_error` và metadata về mức độ đầy đủ.
Số review thu được và trạng thái lượt chạy không đủ để khẳng định đã lấy mọi
review trên Lazada. Nếu bị chặn, hết thời gian/hạn mức hoặc không xác minh được
đã thu thập đủ, cần đọc cảnh báo và metadata của chính lượt đó. Kết quả các lần
phân tích trước vẫn xem được trong **Lịch sử phân tích**.

Luồng URL luôn dùng TinyFish, không tự chuyển sang crawler cookie cũ. Mã
`cookie_crawler.py` còn trong repo phục vụ tham khảo/kiểm thử legacy, không được
chọn làm nguồn thu thập đang hoạt động. TinyFish không bảo đảm lấy hết review,
truy cập được mọi sản phẩm hoặc vượt CAPTCHA. Hướng dẫn này không khẳng định
đã kiểm chứng thành công một lượt thu thập Lazada thật.

## API

API website dùng cookie đăng nhập; client riêng có thể dùng Bearer cá nhân.
Swagger: http://localhost:8000/docs.

- `POST /products/analyze`: JSON `{ "url": "https://www.lazada.vn/products/...-i123.html" }`.
- `POST /collections/import?product_name=Tai%20nghe&format=xlsx`: body bytes file,
  `Content-Type: application/octet-stream`. Không dùng multipart.
- `GET /collections/status`: giới hạn nhập file.
- `POST /collections/reviews`: API JSON giữ tương thích client cũ, không phải
  bước sử dụng website; nhận `product_name` và `reviews`, `product_url` tùy chọn.
- JSON và `product_url` ở API import được giữ để client cũ tiếp tục hoạt động;
  giao diện mới chỉ yêu cầu tên sản phẩm và CSV/Excel.

Import trả `collection`: received, accepted, inserted, duplicates_in_batch,
duplicates_in_database, blank và generated_ids. Lần nhập lỗi rollback cả dữ
liệu và audit; không tạo lịch sử thành công giả.

## Kiểm thử

```bash
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:///:memory: backend python -m unittest discover -s tests -v
docker compose run --rm --no-deps crawler-service python -m unittest discover -s tests -v
python3 backend/tests/run_auth_e2e.py
```

Kiểm thử crawler dùng phản hồi TinyFish giả lập để kiểm tra cấu hình,
chuẩn hóa review và xử lý dữ liệu thiếu/lỗi; không gọi TinyFish hoặc Lazada thật.
Các test cookie còn lại chỉ dành cho mã legacy. E2E dùng schema tạm, file thật
và AI thật; không ghi vào dữ liệu người dùng. Test offline thành công không
chứng minh TinyFish truy cập được một sản phẩm Lazada thật.
