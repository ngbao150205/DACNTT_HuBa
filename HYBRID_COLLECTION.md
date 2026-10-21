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

## 2. URL — hàm crawl và cookie trong .env

Luồng mặc định: website → backend → crawler-service → hàm
`crawl_lazada_reviews()` trong [cookie_crawler.py](crawler-service/cookie_crawler.py)
→ AI/rule → PostgreSQL. Không dùng Chrome Extension hay n8n.

Trong `.env` gốc dự án:

```dotenv
LAZADA_COOKIE='gia_tri_Cookie_tu_phien_trinh_duyet_cua_ban'
# LAZADA_USER_AGENT=User-Agent của cùng trình duyệt nếu cần
```

Chỉ lấy cookie từ phiên bạn có quyền sử dụng; không gửi cookie vào chat/Git.
Trong DevTools của trình duyệt → Network → request đánh giá Lazada thành công,
sao chép **giá trị** header Cookie vào LAZADA_COOKIE, không thêm chữ `Cookie:`.
Không paste cả lệnh curl vào biến này.

Nếu cập nhật từ bản cũ, áp dụng một lần:

```bash
docker compose up -d --build backend frontend crawler-service
```

Sau đó chỉ sửa/lưu `LAZADA_COOKIE` trong `.env` khi cần đổi phiên. Crawler đọc
lại file ở **mỗi lần bắt đầu crawl mới**, không cần restart/build cho thay đổi
cookie. Crawl đang chạy dùng cookie đã đọc lúc bắt đầu. Không cần thay cookie
nếu phiên hiện tại vẫn còn dùng được.

Compose mount thư mục dự án read-only tại `/run/duancntt/config`, để cả thao tác
lưu `.env` bằng atomic rename của IDE cũng được nhận. Chỉ đọc hai biến
LAZADA_COOKIE/LAZADA_USER_AGENT trong file này cho request Lazada; không gửi các
biến database/SMTP đến Lazada. Backend không nhận cookie từ form người dùng và
không trả/log cookie. Biến cấu hình service khác vẫn cần recreate container khi đổi.

Hàm dựa trên code đã cung cấp, phân trang riêng các mức sao **1–5**, page size 5,
`max_pages=None`, chỉ giữ bình luận có nội dung. Nghỉ 1.5–3.5 giây giữa trang và
10–20 giây giữa mức sao. Có CSV xuất kèm trong volume crawler tại
`/var/lib/crawler/exports/<product_id>_1.csv`, ghi atomically khi có dữ liệu.

Khi gặp HTML xác minh, 403/429, trang lặp hoặc lỗi cấu trúc, dừng lượt crawl;
có review thì giữ và trả PARTIAL. Chưa có review thì báo lỗi thích hợp; thiếu
cookie trả 503. Cookie không đảm bảo Lazada luôn cho phép truy cập. Không tự
giải CAPTCHA, đổi IP, thử nhiều phiên hoặc bỏ qua chặn. HTTP Retry-After của
nguồn được chuyển tới backend/giao diện nếu có.

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

Test crawler dùng HTTP giả lập: đọc cookie mới, đủ 5 sao, hơn 50 bình luận,
phân trang, trang lặp và dừng khi bị chặn. E2E dùng schema tạm, file thật và AI
thật; không gửi request Lazada hoặc ghi vào dữ liệu người dùng.
