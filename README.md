# DuanCNTT — Hệ thống phân tích đánh giá sản phẩm Tiki

Ứng dụng thu thập đánh giá tiếng Việt từ Tiki, phân tích cảm xúc bằng model
`underthesea_bilstm_custom_vocab_v3`, áp dụng rule ở backend khi model chưa đủ
tin cậy, phân loại vấn đề và phát hiện rủi ro. Kết quả được lưu trong PostgreSQL
để xem dashboard, review và lịch sử các lần phân tích.

## Chạy nhanh — 3 bước

Cài Git, mở Docker Desktop/Engine, rồi chạy:

```bash
# 1. Clone source kèm model v3
git clone ...
cd DuanCNTT

# 2. Tạo .env từ cấu hình mẫu
cp .env.example .env

# 3. Khởi chạy toàn bộ hệ thống
docker compose up -d
```

Mở **http://localhost:5173** sau khi các service sẵn sàng. Lần đầu Docker tự
build image, PostgreSQL tạo database và backend tự tạo các bảng còn thiếu.
Không cần chạy lệnh build hay tạo bảng riêng. Model v3 đã đi kèm source.

`.env.example` có sẵn cấu hình chạy local; có thể sửa thông tin kết nối trong
`.env` nếu cần. Trên PowerShell, thay lệnh copy bằng `Copy-Item .env.example .env`.
Lần đầu có thể mất vài phút để tải dependency và nạp 5 fold của model.

Các mục bên dưới là tài liệu tham khảo, không phải các bước bắt buộc bổ sung.

## Mục lục

1. [Chức năng và phạm vi](#1-chức-năng-và-phạm-vi)
2. [Kiến trúc và cấu trúc mã nguồn](#2-kiến-trúc-và-cấu-trúc-mã-nguồn)
3. [Chuẩn bị máy, mã nguồn và model](#3-chuẩn-bị-máy-mã-nguồn-và-model)
4. [Triển khai lần đầu bằng Docker Compose](#4-triển-khai-lần-đầu-bằng-docker-compose)
5. [Kiểm tra và sử dụng](#5-kiểm-tra-và-sử-dụng)
6. [Luồng xử lý và model AI](#6-luồng-xử-lý-và-model-ai)
7. [Database và lịch sử](#7-database-và-lịch-sử)
8. [API](#8-api)
9. [Biến môi trường và cấu hình mạng](#9-biến-môi-trường-và-cấu-hình-mạng)
10. [Chạy từng service để phát triển](#10-chạy-từng-service-để-phát-triển)
11. [Kiểm thử](#11-kiểm-thử)
12. [Vận hành, cập nhật và phân tích lại](#12-vận-hành-cập-nhật-và-phân-tích-lại)
13. [Backup và khôi phục](#13-backup-và-khôi-phục)
14. [Triển khai trên máy chủ](#14-triển-khai-trên-máy-chủ)
15. [Xử lý lỗi thường gặp](#15-xử-lý-lỗi-thường-gặp)
16. [Checklist bàn giao](#16-checklist-bàn-giao)

## 1. Chức năng và phạm vi

| Chức năng | Cách hoạt động |
| --- | --- |
| Phân tích sản phẩm | Nhập URL Tiki, crawl review, phân tích và lưu database |
| Sentiment | `Positive`, `Neutral`, `Negative` từ model và decision layer |
| Dashboard | Tổng số review, phân bố sentiment, nhóm vấn đề và rủi ro |
| Review | Xem nội dung, rating, sentiment, issue/risk; API có phân trang và lọc rating |
| Lịch sử | Xem sản phẩm đã lưu và snapshot thống kê của từng lần phân tích |
| Issue | Rule nhận diện chất lượng, giao hàng, dịch vụ/đổi trả và giá/khuyến mãi |
| Risk | Rule trả `HIGH`, `MEDIUM`, `LOW` cùng `risk_flag` |
| Category | Suy luận nhóm sản phẩm bằng từ khóa trong tên/URL |

Category hiện có `FMCG`, `PHONE`, `EARPHONE`, `CLOTHING`, `JEWELRY` và mặc định
`GENERAL`; xem [category_service.py](backend/app/services/category_service.py).
Mã issue trả về gồm `PRODUCT_QUALITY`, `SHIPPING_LOGISTICS`,
`CUSTOMER_SERVICE_RETURNS`, `PRICING_PROMOTIONS`. Với risk, `LOW` và
`risk_flag=false` là kết quả không phát hiện cảnh báo, không phải một review
bị đánh dấu rủi ro chỉ vì có bản ghi trong bảng `risk_detection`.

Các giới hạn cần hiểu khi sử dụng:

- Crawler hiện thực cho **Tiki**; tên model/dataset không có nghĩa đã hỗ trợ crawl các sàn khác.
- Trang `Competitor` hiện là placeholder; chưa có quy trình so sánh đối thủ hoàn chỉnh.
- Chưa có luồng đăng nhập, phân quyền hoặc quản lý nhiều tài khoản.
- Phân tích là request đồng bộ, xử lý review lần lượt; chưa có hàng đợi tác vụ/background job.
- Crawler mặc định thử tối đa **20 trang × 20 review/trang**. Sau khi lọc nội dung
  rỗng và review trùng, số review lưu được có thể thấp hơn; không đồng nghĩa toàn
  bộ review công khai của sản phẩm đã được thu thập.
- Repo hiện chứa inference, kiểm thử và bộ weights v3 đi kèm source; chưa có
  pipeline train đầy đủ để tái tạo model từ dataset ngay sau khi clone.

## 2. Kiến trúc và cấu trúc mã nguồn

```text
Trình duyệt → Frontend React → Backend FastAPI
                                ├─ Crawler Service → Tiki API
                                ├─ AI Service → 5 fold của model v3
                                ├─ Decision Layer → final sentiment
                                ├─ Issue / Risk Rules
                                └─ PostgreSQL → dashboard / review / lịch sử
```

### Các service

| Service Compose | Công nghệ chính | Địa chỉ từ máy host | Địa chỉ trong mạng Docker |
| --- | --- | --- | --- |
| `frontend` | React 19, TypeScript 6, Vite 8, Tailwind, Recharts | `http://localhost:5173` | `http://frontend:5173` |
| `backend` | Python 3.12, FastAPI, SQLAlchemy | `http://127.0.0.1:8000` | `http://backend:8000` |
| `ai-service` | TensorFlow 2.21.0, Keras 3.13.2, Underthesea | `http://127.0.0.1:8001` | `http://ai-service:8001` |
| `crawler-service` | FastAPI, curl_cffi | `http://127.0.0.1:8002` | `http://crawler-service:8002` |
| `postgres` | PostgreSQL 16 | `127.0.0.1:5433` | `postgres:5432` |

Phiên bản phụ thuộc chi tiết nằm trong `*/requirements.txt` và
`frontend/package-lock.json`. Dockerfile là tham chiếu môi trường chạy.

### Cây thư mục

```text
DuanCNTT/
├── README.md
├── .env.example
├── docker-compose.yml
├── .dockerignore
├── frontend/
│   ├── src/pages/                 # Analyze, History, Dashboard, Reviews, Issues, Risk...
│   ├── src/services/api.ts        # Gọi backend và kiểu dữ liệu
│   ├── src/layouts/               # Bố cục và điều hướng
│   ├── package.json
│   └── Dockerfile
├── backend/
│   ├── app/main.py                # FastAPI, tự tạo schema, CORS, router
│   ├── app/api/products.py        # API sản phẩm / phân tích / review / lịch sử
│   ├── app/services/
│   │   ├── product_service.py     # Điều phối crawl → AI → lưu / tổng hợp
│   │   ├── ai_client.py           # Gọi AI rồi quyết định final ở backend
│   │   ├── decision_layer.py      # Gate confidence 0.8 và sentiment guards
│   │   ├── crawler_client.py
│   │   ├── issue_service.py
│   │   ├── risk_service.py
│   │   └── product_analysis_service.py
│   ├── app/rules/                 # JSON rule sentiment, issue, risk đang dùng
│   ├── scripts/                   # Phân tích lại dữ liệu đã lưu
│   └── create_tables.py
├── ai-service/
│   ├── main.py                    # GET /health, POST /predict
│   ├── custom_vocab_predictor.py  # Predictor đang hoạt động
│   ├── ensemble_predictor.py      # Wrapper tương thích, vẫn chỉ gọi model v3
│   ├── models/underthesea_bilstm_custom_vocab_v3/
│   └── README.md                  # Chi tiết inference
├── crawler-service/
│   ├── main.py                    # Entry point thực tế trong Docker
│   └── tiki_crawler.py
├── database/
│   ├── models.py                  # Khai báo 6 bảng SQLAlchemy
│   ├── connection.py              # Engine / session / get_db
│   ├── init_db.py
│   └── init/01-restore-backup.sh   # Import backup tùy chọn khi volume mới
└── backups/                       # Tự tạo nếu bản clone chưa có
```

Các predictor/model cũ có thể còn trong repo để tham khảo, nhưng không được nạp
trong luồng `/predict`. Rule sentiment đang hoạt động nằm trong **backend**;
file `ai-service/decision_layer.py` không tham gia luồng hiện tại.

## 3. Chuẩn bị máy, mã nguồn và model

### 3.1. Yêu cầu

- Git để clone repo.
- Docker Engine/Desktop đang chạy và Docker Compose v2 (`docker compose`).
- Internet để tải image, Python/npm packages và crawl Tiki.
- Các cổng host `5173`, `8000`, `8001`, `8002`, `5433` chưa bị ứng dụng khác chiếm.
- Khuyến nghị dành khoảng 8 GB RAM cho môi trường Docker và ít nhất 10 GB dung
  lượng trống cho image, cache build và dữ liệu. Đây là gợi ý vận hành, không phải
  cấu hình tối thiểu đã benchmark. Inference hiện có thể chạy bằng CPU.

Các lệnh dưới viết cho Bash trên Linux/macOS hoặc Windows qua WSL2.
Nếu dùng PowerShell, thao tác copy `.env` tương ứng là
`Copy-Item .env.example .env`; nên dùng `curl.exe` thay cho alias `curl`.

Kiểm tra công cụ:

```bash
git --version
docker version
docker compose version
```

### 3.2. Model đi kèm source

Nhánh `dev` chứa source và bộ model v3. Người bàn giao cần push đủ mã nguồn và
artifact trước khi người khác clone; không cần tải weights riêng hoặc dùng Git LFS.

<details>
<summary>Chi tiết bộ model — chỉ cần xem khi thay model hoặc kiểm tra lỗi thiếu file</summary>

```text
ai-service/models/underthesea_bilstm_custom_vocab_v3/
├── fold1.keras
├── fold2.keras
├── fold3.keras
├── fold4.keras
├── fold5.keras
├── vocab.json
├── label_encoder.pkl
└── inference_config.json
```

Cấu hình inference dùng 5 fold, padding/truncating `post`. Không trộn weights,
vocab hoặc label encoder của các bản khác nhau. `suspect_labels.csv` không cần
cho inference. Weights/encoder v3 được đánh dấu binary trong `.gitattributes`.

</details>

## 4. Triển khai lần đầu bằng Docker Compose

Chỉ cần ba bước ở [Chạy nhanh](#chạy-nhanh--3-bước). Lệnh `docker compose up -d`
tự thực hiện các việc sau:

1. Build image chưa có trên máy, dùng cấu hình từ `.env` gốc.
2. Khởi tạo PostgreSQL và volume lưu dữ liệu; đợi database, AI và crawler healthy.
3. Backend tự tạo các bảng còn thiếu trước khi nhận request.
4. Khởi động frontend tại **http://localhost:5173**.

Không cần tạo `backend/.env`, tạo thư mục backup hay chạy `create_tables.py`
riêng. Nếu có backup `backups/sentiment_ai_backup.sql`, cơ chế import lần đầu
vẫn hoạt động như [mục 13](#13-backup-và-khôi-phục).

Nếu cần xem tiến độ khởi động:

```bash
docker compose ps
docker compose logs -f backend ai-service
```

Backend/frontend hiện chỉ có trạng thái `Up`; PostgreSQL, AI và crawler có
healthcheck. Với source đã có image cũ trên máy, xem cách build lại tại
[mục 12](#12-vận-hành-cập-nhật-và-phân-tích-lại).

## 5. Kiểm tra và sử dụng

### 5.1. Health và database

```bash
curl -fsS http://127.0.0.1:8000/
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:8002/
curl -fsS http://127.0.0.1:8000/products
```

- AI health phải báo `model_name = underthesea_bilstm_custom_vocab_v3` và 5 checkpoint.
- Với database vừa tạo, `/products` trả `{"products":[]}` là bình thường.
- Backend hoàn tất tạo schema trước khi phục vụ; `/products` kiểm tra truy vấn database hiện tại.
- Nếu vừa khởi động mà chưa kết nối được, xem log và đợi service sẵn sàng.

### 5.2. Test riêng model AI

```bash
curl -fsS http://127.0.0.1:8001/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"sản phẩm rất tốt giao hàng nhanh","rating":5}'
```

Đây là kết quả **model thuần**, chưa qua rule backend. Nhãn và confidence cụ thể
phụ thuộc văn bản, checkpoint và môi trường tiền xử lý.

### 5.3. Test model + rule backend, không lưu database

```bash
docker compose exec -T backend python - <<'PY'
import json
from app.services.ai_client import predict_sentiment

for text, rating in [("sản phẩm rất tốt giao hàng nhanh", 1), ("đeo không đau tai", 5)]:
    result = predict_sentiment(text, rating=rating)
    print(json.dumps({
        "text": text,
        "model_result": result["model_result"],
        "final": result["final"],
    }, ensure_ascii=False, indent=2))
PY
```

So sánh `model_result.confidence`, `final.rules_applied`, `final.method` và
`final.sentiment` để biết nhánh nào được chọn.

### 5.4. Phân tích sản phẩm trên giao diện

1. Mở trang chủ, chọn **Bắt đầu phân tích** (`/analyze`).
2. Dán URL sản phẩm Tiki dạng `https://tiki.vn/ten-san-pham-p123456789.html`.
   Giữ query `?spid=...` nếu URL có, vì nó xác định biến thể sản phẩm.
3. Nhấn phân tích và đợi request hoàn tất. Không bấm gửi liên tục trong lúc xử lý.
4. Giao diện điều hướng đến `/products/{product_db_id}/dashboard`.
5. Xem Reviews, Issues, Risk và trang History (`/history`).

Lần đầu có thể mất vài phút do crawl nhiều trang và chạy 5 fold cho từng review.
Tiki có thể trả dữ liệu thiếu hoặc chặn request; đây không phải tác vụ offline.

Nếu muốn gọi bằng terminal, thay URL ví dụ dưới bằng URL Tiki thực tế còn hợp lệ:

```bash
curl -sS --max-time 600 http://127.0.0.1:8000/products/analyze \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://tiki.vn/ten-san-pham-p123456789.html?spid=123456790"}'
```

Lấy **`product_db_id`** trong response để gọi các API tiếp theo; đây là ID nội bộ,
khác `product_id`/`platform_product_id` của Tiki.

```bash
SENTIMENT_PRODUCT_DB_ID=1 # Thay bằng product_db_id thực tế
curl -fsS "http://127.0.0.1:8000/products/${SENTIMENT_PRODUCT_DB_ID}/analysis"
curl -fsS "http://127.0.0.1:8000/products/${SENTIMENT_PRODUCT_DB_ID}/histories"
curl -fsS "http://127.0.0.1:8000/products/${SENTIMENT_PRODUCT_DB_ID}/reviews?page=1&page_size=10"
```

## 6. Luồng xử lý và model AI

### 6.1. Luồng phân tích sản phẩm

1. `POST /products/analyze` nhận URL.
2. Backend gọi crawler; crawler tách Tiki product ID và `spid`, lấy tên/review,
   loại review rỗng và trùng trong lần crawl.
3. Backend tìm/tạo Product, suy luận category từ tên/URL.
4. Review mới hoặc thiếu sentiment được gửi sang AI. Review đã hoàn thiện dữ
   liệu phân tích được tái sử dụng, không tự chạy lại model mỗi lần crawl.
5. Backend `ai_client.py` nhận model output, gọi `decision_layer.py` để quyết định final.
6. Backend lưu `ReviewAnalysis`, chạy issue/risk dựa trên nội dung và final sentiment,
   cập nhật trạng thái review.
7. Tổng hợp thống kê và ghi `AnalysisHistory`; frontend đọc dữ liệu đã lưu.

Các API xem dashboard, review và history không crawl và không tự gọi AI lại.

### 6.2. Model đang hoạt động

- Model: **`underthesea_bilstm_custom_vocab_v3`**.
- 5 checkpoint; lấy trung bình vector xác suất rồi chọn lớp có xác suất lớn nhất.
- Nhánh A: word embedding → BiLSTM → Attention → average pooling.
- Nhánh B: word embedding → TextCNN với kernel 2/3/4 → max pooling.
- Nhánh C: char embedding → CharCNN với kernel 3/4/5 → max pooling.
- Hợp nhất các nhánh → Dense → softmax 3 lớp.
- Word vocab: 4.521 token; char vocab: 95 token; PAD `0`, OOV `1`.
- Đầu vào: `word_in` dài 64 token và `char_in` dài 160 ký tự.
- Model được nạp một lần khi AI service khởi động.

Tiền xử lý: NFC, lowercase, rút gọn ký tự lặp từ 3 lần trở lên thành 2, giữ chữ
tiếng Việt/Latin/số, chuẩn hóa khoảng trắng. Nhánh word dùng Underthesea và gộp
phủ định như `không` + `tốt` → `không_tốt`; nhánh char dùng text clean. Cả hai
padding/truncating `post`.

Bản artifact v3 chưa kèm code tiền xử lý riêng; pipeline đang giữ theo code
huấn luyện đã được cung cấp trước đó và cấu trúc/vocab tương thích. Khi thay
model, phải xác nhận lại pipeline này với code huấn luyện tương ứng.

Keras được cố định **3.13.2** theo metadata checkpoint; TensorFlow **2.21.0**.
Bản Keras nightly từng cho cảnh báo masking và kết quả khác trên cùng đầu vào,
nên không tự đổi runtime sang nightly.

### 6.3. Quyết định final ở backend

| Confidence model gốc | Xử lý | Method thường gặp |
| --- | --- | --- |
| `>= 0.8` | Giữ nguyên sentiment/confidence model; không chạy sentiment guards | `model_high_confidence` |
| `< 0.8`, có guard khớp | Áp dụng rule text/rating, có thể đổi sentiment/confidence | Tên guard đã áp dụng |
| `< 0.8`, không guard khớp | Giữ kết quả model | `model_low_confidence_no_override` |

So sánh trước khi làm tròn: **đúng 0.8 dùng model**, còn `0.799999` vẫn chạy rule.
Confidence là xác suất lớn nhất sau khi trung bình 5 fold, không phải cam kết
accuracy 80%. Rating không đi vào model; chỉ có thể tác động ở nhánh rule backend.

Các guard hiện có: phủ định tích cực (`không đau tai`...), xung đột rating cao
với nhãn Negative, rating thấp với Positive và xử lý rating 3.

Nguồn điều chỉnh:

- [Decision layer](backend/app/services/decision_layer.py): `MODEL_CONFIDENCE_THRESHOLD = 0.8` và logic guard.
- [Sentiment rules](backend/app/rules/sentiment_decision_rules.json): từ/cụm từ và ngưỡng rating.
- [Issue rules](backend/app/rules/issue_rules.json) và [issue service](backend/app/services/issue_service.py).
- [Risk rules](backend/app/rules/risk_rules.json) và [risk service](backend/app/services/risk_service.py).

Issue/risk có luồng rule riêng sau khi có final; bypass sentiment rule không có
nghĩa bỏ qua phát hiện issue/risk.

Backend giữ `model_result`, `raw_sentiment`, `raw_confidence`, `rules_applied`
để đối chiếu, và trả `final` sau xử lý. Confidence do guard gán không phải
confidence gốc của model. Database hiện lưu nhãn/confidence **final**, model version
và method; chưa có cột riêng lưu toàn bộ raw probability/evidence.

### 6.4. Review không thể phân tích

Review chỉ emoji/dấu câu có thể rỗng sau clean. AI trả HTTP 422 với thông báo
`Review text is empty after preprocessing`; backend nhận diện trường hợp này,
giữ review gốc, không tạo sentiment giả và tiếp tục các review còn lại.

Response phân tích có `unanalyzable_reviews` và `unanalyzable_review_ids`.
Vì vậy `total_reviews` có thể lớn hơn `analyzed_reviews`. Các lỗi AI khác không
bị bỏ qua theo cơ chế này; cần đọc detail/log để xử lý.

## 7. Database và lịch sử

| Bảng | Vai trò |
| --- | --- |
| `products` | Tiki ID, URL, tên, category, trạng thái và thời điểm crawl |
| `reviews` | Nội dung gốc, rating, ngày review và trạng thái phân tích |
| `review_analysis` | Sentiment/confidence final, `model_version`, `analysis_method` |
| `issue_analysis` | Nhóm issue và keyword khớp |
| `risk_detection` | `risk_flag`, mức rủi ro và keyword |
| `analysis_history` | Snapshot số lượng/tỷ lệ sentiment và summary issue/risk theo lần phân tích |

Product có khóa duy nhất theo `(platform, platform_product_id)`; Review theo
`(platform, platform_review_id)`. Đổi model/rule không tự phân tích lại dữ liệu cũ.
Tỷ lệ sentiment được tổng hợp trên review đã có analysis; có thể lệch nhẹ tổng
100% do làm tròn.

`analysis_history` lưu thống kê tổng hợp, không đóng băng đầy đủ nội dung và
kết quả của từng review ở thời điểm cũ. Các script rebuild không tự tái tạo
snapshot lịch sử. Chi tiết model/schema: [database/models.py](database/models.py).

Backend dùng SQLAlchemy `create_all()` khi khởi động: tạo bảng còn thiếu và giữ
nguyên dữ liệu hiện có. Cơ chế này không tự migrate cột của bảng đã tồn tại;
đổi cấu trúc schema cần migration phù hợp.

Dữ liệu PostgreSQL nằm trong named volume `postgres_data` của Compose project,
không nằm trong image backend. `docker compose down` giữ volume; `down -v` xóa
volume và dữ liệu. Không dùng `down -v` như thao tác sửa lỗi thông thường.

## 8. API

Swagger/OpenAPI khi service chạy:

- Backend: http://127.0.0.1:8000/docs
- AI: http://127.0.0.1:8001/docs
- Crawler: http://127.0.0.1:8002/docs

### Backend — cổng 8000

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| GET | `/` | Process backend đang chạy |
| GET | `/products` hoặc `/products/` | Danh sách sản phẩm đã lưu |
| POST | `/products/analyze` | Body `{"url":"URL_TIKI"}`; crawl, phân tích, ghi database |
| GET | `/products/{product_id}/analysis` | Dashboard; có query `history_id` để chọn snapshot |
| GET | `/products/{product_id}/histories` | Danh sách snapshot của sản phẩm |
| GET | `/products/{product_id}/reviews` | Query `page=1`, `page_size=10`, `rating` tùy chọn |

`{product_id}` trên URL API là **ID nội bộ database**. `page_size` được giới hạn
tối đa 100. Sản phẩm không tồn tại trả 404. Các lỗi xử lý trả detail trong JSON;
frontend Analyze hiển thị detail chuỗi từ backend.

### AI — cổng 8001

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| GET | `/` | Tên service, model và checkpoint |
| GET | `/health` | Model đã được nạp và service sẵn sàng |
| POST | `/predict` | Body `{"text":"...","rating":5}` |

`text` dài 1–5.000 ký tự; rating tùy chọn trong khoảng 1–5. AI trả sentiment,
confidence, probabilities, model name, checkpoint và `final` của model thuần.
Chỉ khi đi qua backend client thì `final` mới được quyết định lại theo confidence/rule.

### Crawler — cổng 8002

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| GET | `/` | Trạng thái process |
| POST | `/crawl` | Body `{"url":"URL_TIKI"}`; trả product ID, spid, tên và reviews |

Crawler có retry, sleep giữa trang, loại duplicate/rỗng và có thể trả
`crawl_status = PARTIAL`, `crawl_error`, `stopped_at_page`. `FULL` cũng không
đảm bảo đã lấy hết review vượt giới hạn 20 trang. Backend gọi crawler với timeout
120 giây; mỗi lần gọi AI có timeout 60 giây.

## 9. Biến môi trường và cấu hình mạng

| Biến | Dùng ở đâu / ý nghĩa |
| --- | --- |
| `POSTGRES_USER` | User khởi tạo PostgreSQL |
| `POSTGRES_PASSWORD` | Password user PostgreSQL |
| `POSTGRES_DB` | Database khởi tạo |
| `DATABASE_URL` | SQLAlchemy kết nối PostgreSQL |
| `AI_SERVICE_URL` | Backend gọi `/predict`; trong Compose là `http://ai-service:8001` |
| `CRAWLER_SERVICE_URL` | Backend gọi `/crawl`; trong Compose là `http://crawler-service:8002` |
| `BACKEND_URL` | Có trong `.env.example`, chưa được frontend hiện tại dùng để chọn URL API |
| `APP_ENV` | Có trong `.env.example`, chưa tự chuyển CORS/URL hay thay cấu hình deployment |

File `.env.example` có sẵn cấu hình local cho Compose. Nếu đổi username,
password hoặc database, sửa đồng bộ các biến PostgreSQL và `DATABASE_URL`.
Password có ký tự đặc biệt trong URL cần URL-encode. Không commit `.env` thật.
Trong Docker, dùng `postgres:5432`; backend native trên host dùng `127.0.0.1:5433`.

`database/connection.py` tìm `database/.env` nếu file đó tồn tại, nếu không dùng
`load_dotenv()`. Biến đã có trong process được ưu tiên. Với Docker, dùng `.env`
gốc qua Compose; với native, export đúng giá trị như mục 10 để tránh hostname Docker.

Frontend hiện hard-code `http://127.0.0.1:8000` tại:

- `frontend/src/services/api.ts`.
- `frontend/src/pages/Analyze.tsx`.

Backend CORS tại `backend/app/main.py` chỉ cho `http://localhost:5173` và
`http://127.0.0.1:5173`. Đổi domain/cổng frontend phải cập nhật CORS; đổi địa chỉ
backend phải cập nhật cả hai chỗ gọi API. Chỉ sửa `BACKEND_URL` trong `.env`
**không đổi** URL đang dùng trong trình duyệt.

## 10. Chạy từng service để phát triển

Khuyến nghị Docker nếu chỉ cần sử dụng. Native phù hợp khi sửa code/hot reload.
Ví dụ dưới dành cho Bash/Linux/macOS; mỗi terminal bắt đầu từ thư mục gốc repo.
Dùng Python **3.12** như Dockerfile; không dùng chung venv của dự án khác.
Frontend cần Node `^20.19.0` hoặc `>=22.12.0` theo Vite đang dùng.

### Terminal 1 — PostgreSQL trong Docker

Chuẩn bị `.env` như mục 4, rồi:

```bash
docker compose up -d postgres
```

Đợi healthy. Nếu các container app khác đang chạy, dừng chúng trước để tránh
trùng cổng với các process native:

```bash
docker compose stop frontend backend ai-service crawler-service
```

### Terminal 2 — AI

```bash
cd ai-service
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Phải có đủ bộ model như mục 3.2. Không cần GPU để chạy luồng hiện tại.

### Terminal 3 — Crawler

```bash
cd crawler-service
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8002
```

### Terminal 4 — Backend

Thay thông tin database mẫu bằng bộ giá trị đã đặt trong `.env`:

```bash
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
python -m pip install -r backend/requirements.txt
export DATABASE_URL='postgresql://my_db_user:my_db_password@127.0.0.1:5433/my_database_name'
export AI_SERVICE_URL='http://127.0.0.1:8001'
export CRAWLER_SERVICE_URL='http://127.0.0.1:8002'
python -m uvicorn --app-dir backend app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 5 — Frontend

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Mở http://localhost:5173. Nếu Vite tự chọn cổng khác vì 5173 đang bận, giải phóng
cổng hoặc cập nhật CORS cho cổng mới.

## 11. Kiểm thử

Chạy sau `docker compose up -d` và đợi các service sẵn sàng. Các lệnh dưới
kiểm tra nhanh hệ thống đang chạy; bản source hiện tại không kèm bộ unit test.

### Backend

```bash
curl -fsS http://127.0.0.1:8000/
curl -fsS http://127.0.0.1:8000/products
```

Hai API phải trả HTTP 200. Với database mới, danh sách sản phẩm rỗng là bình thường.

### AI

```bash
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:8001/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"sản phẩm rất tốt giao hàng nhanh","rating":5}'
```

Response phải có `model_name` là `underthesea_bilstm_custom_vocab_v3`.
`/health` liệt kê đủ 5 checkpoint; `/predict` trả sentiment và confidence.
Đây là kết quả model; backend mới áp dụng ngưỡng 0.8 khi phân tích sản phẩm.

### Frontend

```bash
docker compose run --rm --no-deps frontend npm run build
```

Lệnh kiểm tra TypeScript và bundle Vite. Nếu chạy native: `cd frontend`,
`npm ci`, `npm run build`.

### Crawler thật — tùy chọn, cần Internet/Tiki

```bash
curl -fsS http://127.0.0.1:8002/crawl \
  -H 'Content-Type: application/json' \
  -d '{"url":"URL_SAN_PHAM_TIKI_CON_HIEU_LUC"}'
```

Thay `URL_SAN_PHAM_TIKI_CON_HIEU_LUC` bằng URL thật trước khi chạy. Lệnh này
gọi Tiki thật; kết quả phụ thuộc tình trạng sản phẩm và kết nối tới Tiki.

## 12. Vận hành, cập nhật và phân tích lại

### Lệnh thường dùng

```bash
docker compose ps
docker compose logs -f backend ai-service crawler-service
docker compose logs --tail 100 frontend
docker compose restart backend
docker compose stop
docker compose start
docker compose down
```

`stop/start` giữ container; `down` bỏ container/network nhưng giữ named volume.
Với container mới từ đầu dùng `up -d`, không dùng `start`.

### Sau khi sửa source, model hoặc rule

Dockerfile copy source vào image, không bind mount source để tự cập nhật:

```bash
# Thay model, predictor hoặc rule sentiment backend
docker compose up -d --build ai-service backend

# Thay frontend
docker compose up -d --build frontend
```

`restart` không build/copy mã nguồn mới. Model và JSON rule được nạp khi process
khởi động; thay file trên host rồi chỉ mở lại trang web không cập nhật container.

### Phân tích lại review đã lưu

Các script sau **ghi lại dữ liệu phân tích**. Backup database trước khi chạy;
không chạy song song với một đợt phân tích sản phẩm khác.

```bash
# Gọi model v3 + decision layer cho các review đã lưu, không crawl Tiki
docker compose exec -T backend python scripts/rebuild_sentiment_analysis.py

# Dùng sentiment đã lưu để chạy lại issue/risk
docker compose exec -T backend python scripts/rebuild_issue_analysis.py
docker compose exec -T backend python scripts/rebuild_risk_detection.py

# Risk có thể giới hạn theo ID nội bộ sản phẩm
docker compose exec -T backend python scripts/rebuild_risk_detection.py --product-id 1 --batch-size 500
```

Đọc log `rebuilt/skipped/failed`. Script sentiment có thể báo `FAILED` cho review
chỉ emoji vì chưa có cơ chế đếm riêng như API phân tích sản phẩm; nó không gán
sentiment giả. Script issue hiện không truyền category của từng product, cần
đánh giá ảnh hưởng nếu muốn rebuild issue theo nhóm sản phẩm.

Các script không tự cập nhật snapshot cũ trong `analysis_history`. Không xem
việc đổi weights/rule là thao tác tự động sửa mọi kết quả đã lưu.

## 13. Backup và khôi phục

### Backup database đang chạy

```bash
mkdir -p backups
docker compose exec -T postgres sh -c \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges' \
  > backups/sentiment_manual.sql
```

Kiểm tra lệnh thành công và file backup có dữ liệu. File này không được commit
theo `.gitignore`. `--no-owner --no-privileges` giúp chuyển sang môi trường dùng
user PostgreSQL khác mà không cần tạo lại owner của máy nguồn.

### Khôi phục vào database kiểm tra riêng

Ví dụ tạo một database mới tên `sentiment_restore_check`; không ghi đè database
đang dùng:

```bash
docker compose exec -T postgres sh -c \
  'createdb -U "$POSTGRES_USER" sentiment_restore_check'
docker compose exec -T postgres sh -c \
  'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d sentiment_restore_check' \
  < backups/sentiment_manual.sql
```

Kiểm tra schema/dữ liệu trước khi quyết định chuyển ứng dụng sang database đó.
Database kiểm tra chỉ được tạo một lần; nếu tên đã tồn tại, chọn tên mới thay vì
tự xóa dữ liệu. Khi đổi kết nối phải cập nhật `DATABASE_URL` và recreate backend.

### Cơ chế import backup khi PostgreSQL khởi tạo lần đầu

Compose mount `database/init/` và `backups/` vào PostgreSQL. Script
`01-restore-backup.sh` tìm đúng file **`backups/sentiment_ai_backup.sql`** và chạy
nó **chỉ khi data volume còn mới**.

- Không có file: PostgreSQL tạo database trống; backend tự tạo schema khi khởi động.
- Volume đã có dữ liệu: restart/up không chạy lại init script và không import lại backup.
- Script hiện dùng `ON_ERROR_STOP=0`; phải đọc log lỗi, không chỉ dựa vào dòng
  “Import database hoàn tất”. SQL dump cũ có owner/role khác máy đích có thể báo lỗi.
- Không đặt file backup vào thư mục rồi xóa volume để “thử” trên hệ thống có dữ liệu thật.
- Đổi `POSTGRES_USER/PASSWORD/DB` trong `.env` không tự đổi user/password/database
  đã tồn tại trong volume cũ.

Backup chỉ là dữ liệu/schema, không chứa weights model và không thay cho bản
bàn giao source + model + cấu hình.

## 14. Triển khai trên máy chủ

### Chạy demo trên server qua SSH tunnel

Trên server: làm toàn bộ mục 3–5. Trên máy người xem, mở tunnel:

```bash
ssh -N \
  -L 5173:127.0.0.1:5173 \
  -L 8000:127.0.0.1:8000 \
  user@your-server
```

Sau đó mở http://localhost:5173 trên máy người xem. Tunnel cả 8000 là cần thiết
vì trình duyệt đang gọi backend tại `127.0.0.1:8000`; chỉ tunnel cổng frontend
sẽ không đủ. Không cần mở AI/crawler/database ra ngoài để trình duyệt sử dụng.

### Phục vụ bằng domain/IP cho nhiều máy

Cấu hình hiện tại dùng Vite dev server và URL/CORS cố định cho local; chưa phải
một bộ cấu hình production hoàn chỉnh. Khi triển khai public cần thực hiện:

1. Chọn địa chỉ API mà trình duyệt của người dùng truy cập được; sửa cả hai chỗ
   gọi API nêu ở mục 9 hoặc bổ sung cơ chế cấu hình phù hợp.
2. Thêm origin frontend thực tế vào CORS backend.
3. Build frontend bằng `npm run build`; phục vụ `frontend/dist` bằng web server
   có SPA fallback về `index.html`, thay cho Vite dev server.
4. Cấu hình reverse proxy, HTTPS và timeout đủ cho request phân tích đồng bộ.
   Trang HTTPS phải gọi API HTTPS, tránh mixed content.
5. Giới hạn public ports bằng cấu hình bind/firewall; Compose hiện publish cả
   PostgreSQL, AI và crawler trên host. Hệ thống chưa có xác thực để bảo vệ API
   phân tích nếu đưa trực tiếp lên Internet.
6. Thiết lập backup, tài nguyên và theo dõi log trước khi sử dụng lâu dài.

README không giả định việc đổi `APP_ENV=production` sẽ tự thực hiện các bước này.

## 15. Xử lý lỗi thường gặp

Luôn đọc response `detail` và log trước:

```bash
docker compose ps -a
docker compose logs --tail 100 backend ai-service crawler-service postgres
```

| Hiện tượng | Kiểm tra / hướng xử lý |
| --- | --- |
| Docker daemon/socket không kết nối | Mở Docker Desktop/daemon, kiểm tra `docker version` |
| Cổng đã được dùng | Dừng process trùng cổng hoặc đổi host port rồi đồng bộ URL frontend/CORS |
| AI thoát vì thiếu file | Kiểm tra đủ 8 file v3 ở mục 3.2, không chỉ có vocab hoặc model cũ |
| Lỗi shape/input/vocab/label khi nạp model | Dùng nguyên bộ weights, vocab, encoder và cấu hình của cùng lần train |
| Warning masking / Keras load lỗi | Dùng requirements đã cố định; kiểm tra Keras 3.13.2, build lại AI |
| `DATABASE_URL is not configured` | Tạo `.env` đúng chỗ; Compose phải được chạy từ đúng thư mục/cấu hình |
| `relation ... does not exist` khi gọi `/products` | Rebuild backend với source mới và khởi động lại để tự tạo bảng; schema cũ thiếu cột cần migration |
| `failed to resolve host 'postgres'` | Backend và PostgreSQL phải cùng mạng Compose, alias `postgres` phải tồn tại |
| Kết nối DB sai password sau sửa `.env` | Volume cũ vẫn giữ user/password cũ; cập nhật thông tin kết nối hoặc đổi password DB có kiểm soát |
| `localhost` kết nối thất bại trong backend container | `localhost` là chính container; dùng `postgres`, `ai-service`, `crawler-service` trong Compose |
| Trình duyệt báo CORS/Failed to fetch | Kiểm tra backend có chạy, origin được cho phép và URL API đang hard-code ở frontend |
| `/products/analyze` trả 500 | Đọc detail/log: kết nối DB, crawler timeout/Tiki, AI validation/runtime; không chỉ dựa vào dòng console Analyze.tsx |
| `/predict` trả 422 cho emoji | Bình thường với nội dung rỗng sau clean; API phân tích sản phẩm hiện bỏ qua sentiment của review đó |
| Crawl không có/thiếu review | Kiểm tra URL, giữ `spid`, giới hạn 20 trang, dữ liệu Tiki, trạng thái PARTIAL và log crawler |
| Build timeout khi tải package | Kiểm tra mạng/DNS Docker, chạy lại build; tránh nâng dependency ngẫu nhiên |
| Sửa code mà giao diện/AI không đổi | Build và recreate đúng service; restart hoặc refresh trình duyệt không copy source vào image |
| `Cannot find module`/`ModuleNotFoundError` khi native | Đúng thư mục, đúng venv và entry point; không chạy backend bằng venv Python 3.14 của dự án khác |
| TypeScript báo biến không dùng | Sửa biến/import không dùng rồi chạy `npm run build`; không bỏ kiểm tra chỉ để tạo bundle |

Để kiểm tra mạng khi hostname `postgres` không phân giải:

```bash
docker inspect sentiment-backend sentiment-postgres --format '{{.Name}} {{json .NetworkSettings.Networks}}'
docker network ls
```

Nếu xác nhận PostgreSQL bị tách khỏi mạng, nối lại **đúng mạng của Compose project**
với alias `postgres`, hoặc recreate service đúng project sau khi bảo đảm volume
dữ liệu vẫn được sử dụng. Không cố định IP container vì IP có thể thay đổi.

Giới hạn schema/backend validation của `/predict` vẫn áp dụng: text quá dài,
rating ngoài khoảng 1–5 hoặc response không hợp lệ là lỗi khác với emoji-only.
Không bỏ qua mọi lỗi AI để biến một đợt phân tích lỗi thành “thành công”.

## 16. Checklist bàn giao

- [ ] Nhánh/commit trên remote có source mới, gồm predictor v3, decision layer backend và rule.
- [ ] Commit/push đủ 8 file model v3 cùng source, kiểm tra bằng một bản clone mới.
- [ ] Xác nhận tiền xử lý khớp code train, cung cấp code/config train nếu có thay đổi.
- [ ] Cung cấp `.env.example` không chứa bí mật; người nhận tự tạo `.env`.
- [ ] Chọn database rỗng hoặc bản backup, không phụ thuộc volume trên máy người phát triển.
- [ ] Kiểm tra database mới được tự tạo bảng sau `docker compose up -d`.
- [ ] Kiểm tra AI `/health` đúng `_v3`, backend `/products` hoạt động.
- [ ] Chạy kiểm tra API backend/AI ở mục 11 và build frontend.
- [ ] Thử một URL Tiki còn hợp lệ và kiểm tra dashboard/history sau khi phân tích.
- [ ] Nếu public domain: hoàn tất URL API, CORS, frontend static/reverse proxy và quản lý truy cập.

Không cần giao `.venv`, `node_modules` hoặc image Docker của máy cá nhân.
Weights v3 được giao bằng Git cùng source; cần bảo đảm commit trên remote thực
sự chứa đủ artifact. Bản clone thiếu weights v3 thì AI service chưa thể khởi động.
