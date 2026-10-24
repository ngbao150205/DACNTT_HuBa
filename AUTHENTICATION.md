# Tài khoản, quyền dữ liệu và khôi phục mật khẩu

## Chạy và sử dụng

Clone dự án, `cp .env.example .env`, rồi `docker compose up -d` như README chính.
Nếu đang cập nhật từ bản cũ: `docker compose up -d --build backend frontend mailpit`.

1. Mở http://localhost:5173, chọn **Đăng ký**, nhập họ tên, email, mật khẩu
   10–128 ký tự và xác nhận. Đăng ký thành công sẽ tự đăng nhập.
2. Tài khoản mới có lịch sử trống. Phân tích URL hoặc tải CSV/Excel sẽ tạo dữ liệu của tài khoản đó. Người khác không xem được dữ liệu này.
3. Bấm tên ở góc phải để vào **Tài khoản**; **Đăng xuất** kết thúc phiên hiện tại.
4. Chọn **Quên mật khẩu** trên trang đăng nhập, nhập email đã đăng ký.
5. Mở http://localhost:8025, chọn thư trong **Mailpit**, bấm liên kết đặt lại mật
   khẩu, nhập mật khẩu mới và xác nhận, rồi đăng nhập lại.

Mailpit là hộp thư thử nghiệm cục bộ, không gửi thư đến Gmail/email thật, không
cần mật khẩu SMTP. UI chỉ publish vào loopback máy Docker. Thư tồn tại trong
container Mailpit và có thể mất khi tạo lại container; yêu cầu email mới nếu cần.
Các email luôn trả thông báo chung để không tiết lộ tài khoản có tồn tại hay không.

## Dữ liệu trước khi có đăng nhập

Migration backend chạy tự động trong một transaction: thêm bảng xác thực và
`products.owner_id`, thay unique sản phẩm bằng `(owner_id, platform, platform_product_id)`
và unique review bằng `(product_id, platform, platform_review_id)`.
Không xóa sản phẩm/review/AI/lịch sử. Database và volume dữ liệu hiện có được giữ nguyên.

Sản phẩm cũ có `owner_id=NULL`, không hiển thị cho tài khoản mới. Sau khi chủ dự
án đăng ký, quản trị viên chạy trên máy có quyền Docker (thay email ví dụ):

```bash
docker compose exec backend python /app/backend/scripts/assign_legacy_data.py --email ban@example.com
```

Lệnh gán **toàn bộ sản phẩm chưa có chủ**, giữ nguyên review và lịch sử. Không
có API cho người đăng ký tự nhận dữ liệu cũ. Nếu tài khoản đã tạo sản phẩm trùng,
lệnh dừng mà không sửa dữ liệu; quản trị viên cần xem xét cách gộp. Nên thực hiện
bước này trước khi chủ dự án phân tích/import cùng sản phẩm cũ.

## Nhập dữ liệu

Website dùng phiên đăng nhập cho cả URL và file CSV/Excel. File chỉ yêu cầu tên
sản phẩm và file dữ liệu, không cần URL hoặc khóa API. Không còn luồng Chrome
Extension. Xem [thu thập URL / file](HYBRID_COLLECTION.md).

API Bearer cá nhân vẫn giữ cho client terminal cũ. Có thể tạo bằng
`POST /auth/api-token` trong Swagger:

1. Đăng nhập website tại `http://localhost:5173`.
2. Trong cùng trình duyệt, mở `http://localhost:8000/docs` (cùng hostname localhost).
3. Mở `POST /auth/api-token` → **Try it out** → **Execute**. Cookie HttpOnly được
   trình duyệt gửi tự động; không cần đọc/copy cookie.
4. Sao chép trường `token` một lần và dùng làm PERSONAL_API_TOKEN cho lệnh curl.

Khóa không được lưu trong source hoặc hiển thị ở trang Tài khoản. Website phân
tích URL/file dùng phiên đăng nhập, không cần thao tác tạo khóa này.

## API

Swagger: http://localhost:8000/docs. Các API `/products/*` và `/collections/*`
đều cần phiên đăng nhập hoặc Bearer cá nhân. Truy cập sản phẩm tài khoản khác
trả **404**; chưa xác thực trả **401**. Cùng URL/review ID ở hai tài khoản tạo
hai tập dữ liệu riêng, chống trùng trong từng tài khoản.

| Endpoint | Body / xác thực | Kết quả |
| --- | --- | --- |
| `POST /auth/register` | `{email, full_name, password}` | 201, user và cookie phiên |
| `POST /auth/login` | `{email, password}` | user và cookie phiên |
| `GET /auth/me` | cookie / Bearer cá nhân | user hiện tại |
| `POST /auth/logout` | cookie | 204, thu hồi phiên hiện tại |
| `POST /auth/forgot-password` | `{email}` | 202, gửi email nếu có tài khoản |
| `POST /auth/reset-password` | `{token, password}` | đặt lại mật khẩu |
| `POST /auth/api-token` | chỉ cookie đăng nhập | khóa mới, `expires_at` |
| `DELETE /auth/api-token` | chỉ cookie đăng nhập | 204, thu hồi khóa |

Mật khẩu băm Argon2id; cookie HttpOnly, SameSite=Lax, hết hạn sau 7 ngày. Token
phiên/khôi phục/API cá nhân chỉ lưu SHA-256 trong PostgreSQL. Token reset có hạn
15 phút, dùng một lần; yêu cầu email mới vô hiệu hóa liên kết cũ. Reset thành
công thu hồi mọi phiên đăng nhập và khóa API cá nhân của tài khoản. Phải đăng nhập
và tạo lại khóa API cá nhân nếu cần.

Link reset dùng fragment `#token=...`, được UI bỏ khỏi thanh địa chỉ khi mở để
không đưa token vào URL request/log/referrer. Không tải lại trang reset sau khi
đã mở; mở lại liên kết email nếu cần. Browser POST ngoài origin được phép bị từ
chối. Cấu hình giới hạn thử trong database: đăng ký 10/IP/giờ, đăng nhập
10/email và 30/IP/5 phút, quên mật khẩu 3/email và 10/IP/15 phút,
reset 20/IP/15 phút; quá giới hạn trả 429 kèm Retry-After. Backend không tin
X-Forwarded-For từ client; khi đặt reverse proxy phải cấu hình IP tin cậy phù hợp.

Đăng xuất hoặc đổi tài khoản được đồng bộ giữa các tab cùng trình duyệt;
trạng thái sản phẩm lưu cục bộ được xóa khi thay phiên.

## Cấu hình

| Biến | Local Compose | Ý nghĩa |
| --- | --- | --- |
| `AUTH_FRONTEND_URL` | `http://localhost:5173` | origin website và gốc liên kết reset |
| `AUTH_COOKIE_SECURE` | `false` | bật `true` khi triển khai HTTPS |
| `SMTP_HOST` / `SMTP_PORT` | `mailpit` / `1025` | máy chủ gửi thư thử nghiệm |
| `SMTP_FROM` | `DuanCNTT <no-reply@duancntt.local>` | người gửi |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | trống | chỉ khi SMTP thật yêu cầu |
| `SMTP_STARTTLS` / `SMTP_SSL` | `false` | chọn kiểu TLS theo SMTP thật |

Chạy backend ngoài Docker: dùng `SMTP_HOST=localhost` và SMTP server local;
Compose không publish cổng SMTP 1025 ra máy mặc định. Website dùng cùng hostname
với API để cookie local hoạt động (localhost hoặc 127.0.0.1, tránh trộn hai host).
Có thể cấu hình `VITE_API_URL` khi chạy Vite trực tiếp; khi build image phải cấp
biến này ở bước build hoặc dùng reverse proxy. Triển khai public nên dùng cùng
site HTTPS cho UI/API, bật Secure cookie, SMTP thật và không public UI Mailpit.

## Kiểm thử

```bash
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:///:memory: backend python -m unittest discover -s tests -v
```

Bộ test auth kiểm tra đăng ký/đăng nhập/đăng xuất, hash, Origin, hạn chế thử,
reset dùng một lần/expiry/thu hồi phiên, Bearer cá nhân và truy cập chéo tài khoản.

Kiểm thử PostgreSQL và luồng trình duyệt đầy đủ (cần các image đã build):

```bash
python3 backend/tests/run_auth_e2e.py
```

E2E tự build image browser-test khi chạy lần đầu, dùng schema/container Mailpit riêng, Chromium sandbox trong container kiểm thử riêng và model
thật; tự xóa dữ liệu thử sau khi hoàn tất, không gọi Lazada.
