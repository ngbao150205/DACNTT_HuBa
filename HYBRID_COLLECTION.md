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

## 2. URL — cookie trong .env

Luồng: website → backend → crawler-service → **API đánh giá Lazada** → review
đã chuẩn hóa → AI/rule backend → PostgreSQL. Crawler đang dùng
`cookie_crawler.py`, không gọi TinyFish, Chrome Extension hoặc n8n.

Nếu chưa có `.env`, chạy `cp .env.example .env`. Trong `.env` ở thư mục gốc,
điền giá trị header Cookie từ request `getReviewList` trả JSON thành công:

```dotenv
LAZADA_COOKIE=''
```

Chỉ cần `LAZADA_COOKIE`; không cần `LAZADA_USER_AGENT` hoặc khóa API TinyFish.
Điền cookie thật giữa hai dấu nháy đơn, trên một dòng, không kèm chữ `Cookie:`
và không dùng backtick. Xem [cách lấy cookie](crawler-service/README.md#cấu-hình).
Giữ cookie cục bộ, không gửi vào Git, chat, log hoặc form phân tích.

Chạy `docker compose up -d`, đăng nhập website và nhập URL sản phẩm Lazada.
Nếu container đang chạy bản cũ hoặc TinyFish, đồng bộ source một lần:

```bash
docker compose up -d --build crawler-service backend frontend
```

Compose đặt `LAZADA_ENV_FILE=/run/duancntt/config/.env`. Crawler đọc lại cookie
trong file được mount **mỗi lần bắt đầu crawl mới**, nên thay cookie không cần
restart hoặc build lại. Lượt đang chạy giữ cấu hình đã đọc lúc bắt đầu.

Crawler lấy các mức 1–5 sao, phân trang đến khi hết dữ liệu và chỉ giữ bình luận
có nội dung, không áp giới hạn 50 review. Nếu gặp xác minh hoặc lỗi truy cập,
crawler dừng và giữ dữ liệu một phần với `PARTIAL`; backend vẫn phân tích/lưu
những review hợp lệ đã lấy. Khi nguồn chưa cung cấp review mới, kết quả đã lưu
vẫn xem được trong **Lịch sử phân tích**. Thiếu cookie trả lỗi cấu hình `503`;
nhập CSV/Excel vẫn hoạt động.

Cookie không bảo đảm Lazada cung cấp hết review hoặc không yêu cầu CAPTCHA.
Không coi số review thu được là tổng số review trên sàn; kiểm tra cảnh báo và
metadata của lượt crawl. Hướng dẫn này không khẳng định đã kiểm chứng một lượt
thu thập Lazada thật thành công.

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
docker compose run --rm --no-deps crawler-service python -m unittest discover -s tests -p test_cookie_crawler.py -v
python3 backend/tests/run_auth_e2e.py
```

Kiểm thử crawler dùng HTTP giả lập/localhost để kiểm tra cấu hình cookie,
phân trang, chuẩn hóa review và dữ liệu một phần; không gọi Lazada hoặc dùng
cookie thật. E2E dùng schema tạm, file thật và AI thật; không ghi vào dữ liệu
người dùng. Test offline không chứng minh đã truy cập Lazada thật thành công.
