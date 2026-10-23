# DuanCNTT — Hệ thống phân tích đánh giá sản phẩm Lazada

Ứng dụng thu thập đánh giá tiếng Việt từ Lazada, phân tích cảm xúc bằng model
`underthesea_bilstm_custom_vocab_v3`, áp dụng rule ở backend khi model chưa đủ
tin cậy, phân loại vấn đề và phát hiện rủi ro. Kết quả được lưu trong PostgreSQL
để xem dashboard, review và lịch sử các lần phân tích.

## Chạy nhanh — 3 bước

Cài Git, mở Docker Desktop/Engine, rồi chạy:

```bash
# 1. Clone source kèm model v3
git clone --branch dev https://github.com/ngbao150205/DACNTT_HuBa.git DuanCNTT
cd DuanCNTT

# 2. Tạo .env, rồi mở file và điền TINYFISH_API_KEY nếu dùng phân tích URL
cp .env.example .env
# Lấy khóa tại https://agent.tinyfish.ai/api-keys (giữ khóa thật trong .env)

# 3. Khởi chạy toàn bộ hệ thống
docker compose up -d
```

Mở **http://localhost:5173** sau khi các service sẵn sàng. Lần đầu Docker tự
build image, PostgreSQL tạo database và backend tự tạo các bảng còn thiếu.
Không cần chạy lệnh build hay tạo bảng riêng. Model v3 đã đi kèm source.

`.env.example` có sẵn cấu hình chạy local. Nhánh URL cần khóa
[TinyFish Agent API](https://agent.tinyfish.ai/api-keys) trong `TINYFISH_API_KEY`;
nhánh tải CSV/Excel không cần khóa. Không cần Cookie hoặc User-Agent Lazada.
Có thể sửa thông tin kết nối trong `.env` nếu cần. Trên PowerShell, thay lệnh copy bằng `Copy-Item .env.example .env`.
Lần đầu có thể mất vài phút để tải dependency và nạp 5 fold của model.

Các mục bên dưới là tài liệu tham khảo, không phải các bước bắt buộc bổ sung.

## Hai cách phân tích dữ liệu

1. **URL sản phẩm:** nhập URL Lazada; crawler gọi TinyFish Agent API, chuẩn
   hóa review, rồi backend phân tích và lưu. Đặt `TINYFISH_API_KEY` trong `.env`
   cục bộ; khóa và timeout được đọc lại mỗi lượt crawl mới, không cần restart.
2. **Tải file CSV / Excel:** nhập tên sản phẩm, chọn `.csv`, `.xlsx` hoặc `.xls`,
   rồi phân tích. Không cần URL, Cookie Lazada hay khóa TinyFish. File cùng tên
   sản phẩm được gộp và loại review trùng trong cùng tài khoản.

Không cần Chrome Extension hay n8n. Luồng URL luôn dùng TinyFish, không fallback
sang crawler cookie cũ. Cả hai cách vẫn lưu PostgreSQL và dùng chung model v3 /
rule backend. TinyFish là dịch vụ bên thứ ba có chi phí/hạn mức; không bảo đảm
lấy mọi review hoặc vượt CAPTCHA. Khi có dữ liệu một phần, hệ thống giữ review
hợp lệ kèm cảnh báo và metadata về mức độ đầy đủ.

Xem [hướng dẫn URL / CSV / Excel](HYBRID_COLLECTION.md). Khóa thật nằm trong
`.env` cục bộ và không được đưa vào Git, log, chat hay giao diện.

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
| Phân tích sản phẩm | Nhập URL Lazada, crawl review, phân tích và lưu database |
| Tải CSV / Excel | Chỉ cần tên sản phẩm và file, gộp/chống trùng và phân tích theo tài khoản |
| Sentiment | `Positive`, `Neutral`, `Negative` từ model và decision layer |
| Dashboard | Phân bố 1–5 sao, điểm sao trung bình, mức cảnh báo rủi ro, cảm xúc, nhóm vấn đề và xu hướng qua các lần phân tích |
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

Dashboard tính điểm sao trung bình và tỷ lệ từng sao trên các review đã lưu có
rating hợp lệ từ 1 đến 5; review thiếu sao được đếm riêng. Biểu đồ rủi ro chỉ
đếm review có `risk_flag=true`, phân theo mức độ. Biểu đồ xu hướng so sánh
tỷ lệ cảm xúc của tập review tại từng lần phân tích, không phải review mới mỗi ngày.

Các lần phân tích mới lưu thêm `rating_summary` vào lịch sử; backend tự bổ sung
cột khi khởi động, giữ nguyên dữ liệu cũ. Với lịch sử cũ chưa có thống kê số sao,
lần mới nhất hiển thị số sao **hiện có** kèm chú thích; các lần cũ hơn hiển thị
thông báo thiếu thống kê, không lấy số liệu hiện tại giả làm dữ liệu lịch sử.

Các giới hạn cần hiểu khi sử dụng:

- Crawler đang hoạt động chỉ nhận URL đầy đủ của **Lazada Việt Nam**. Dữ liệu Tiki đã lưu vẫn xem được; không đổi nhãn sàn cho dữ liệu cũ.
- Trang `Competitor` hiện là placeholder; chưa có quy trình so sánh đối thủ hoàn chỉnh.
- Có đăng ký, đăng nhập, đăng xuất và quên mật khẩu; dữ liệu được tách theo tài khoản.
  Mailpit chỉ nhận email thử nghiệm trên máy local.
- Phân tích là request đồng bộ, xử lý review lần lượt; chưa có hàng đợi tác vụ/background job.
- Crawler dùng TinyFish Agent API với thời gian chờ mặc định **600 giây**,
  cấu hình bằng `TINYFISH_TIMEOUT_SECONDS`. Kết quả còn phụ thuộc truy cập nguồn,
  chi phí/hạn mức TinyFish và khả năng trích xuất. Chỉ giữ review có nội dung,
  loại trùng; dữ liệu thiếu được giữ với `PARTIAL` và metadata để kiểm tra.
  Không có bảo đảm đã lấy mọi review, kể cả khi dịch vụ kết thúc lượt chạy.
- Repo hiện chứa inference, kiểm thử và bộ weights v3 đi kèm source; chưa có
  pipeline train đầy đủ để tái tạo model từ dataset ngay sau khi clone.

## 2. Kiến trúc và cấu trúc mã nguồn

```text
Trình duyệt → Frontend React → Backend FastAPI
                                ├─ Crawler Service → TinyFish Agent API → Lazada
                                ├─ AI Service → 5 fold của model v3
                                ├─ Decision Layer → final sentiment
                                ├─ Issue / Risk Rules
                                └─ PostgreSQL → dashboard / review / lịch sử

CSV / Excel + tên sản phẩm → API xác thực → Backend → cùng pipeline AI / database
```

### Các service

| Service Compose | Công nghệ chính | Địa chỉ từ máy host | Địa chỉ trong mạng Docker |
| --- | --- | --- | --- |
| `frontend` | React 19, TypeScript 6, Vite 8, Tailwind, Recharts | `http://localhost:5173` | `http://frontend:5173` |
| `backend` | Python 3.12, FastAPI, SQLAlchemy | `http://127.0.0.1:8000` | `http://backend:8000` |
| `ai-service` | TensorFlow 2.21.0, Keras 3.13.2, Underthesea | `http://127.0.0.1:8001` | `http://ai-service:8001` |
| `crawler-service` | FastAPI, requests, TinyFish Agent API | `http://127.0.0.1:8002` | `http://crawler-service:8002` |
| `postgres` | PostgreSQL 16 | `127.0.0.1:5433` | `postgres:5432` |
| `mailpit` | Hộp thư reset mật khẩu thử nghiệm | `http://localhost:8025` | SMTP `mailpit:1025` |

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
│   ├── tests/                     # Kiểm thử tích hợp Lazada bằng SQLite
│   └── create_tables.py
├── ai-service/
│   ├── main.py                    # GET /health, POST /predict
│   ├── custom_vocab_predictor.py  # Predictor đang hoạt động
│   ├── models/underthesea_bilstm_custom_vocab_v3/
│   └── README.md                  # Chi tiết inference
├── crawler-service/
│   ├── main.py                    # Entry point thực tế trong Docker
│   ├── tinyfish_crawler.py        # TinyFish Agent API, chuẩn hóa review và metadata
│   ├── cookie_crawler.py          # Mã legacy, không dùng cho luồng URL
│   ├── lazada_common.py           # Kiểm tra URL và chuẩn hóa ngày
│   └── tests/                     # Kiểm thử offline và fixture cho E2E
├── database/
│   ├── models.py                  # 6 bảng hiện có + review_collections audit nhập dữ liệu
│   ├── connection.py              # Engine / session / get_db
│   ├── init_db.py
│   └── init/01-restore-backup.sh   # Import backup tùy chọn khi volume mới
└── backups/                       # Tự tạo nếu bản clone chưa có
```

AI service chỉ giữ predictor và bộ model v3 đang chạy. Rule sentiment đặt tại
`backend/app/services/decision_layer.py` và `backend/app/rules`; không còn
loader hay rule sentiment trùng lặp ở AI service. Chromium chỉ dùng trong
image kiểm thử giao diện tùy chọn, không được cài vào crawler ứng dụng.

## 3. Chuẩn bị máy, mã nguồn và model

### 3.1. Yêu cầu

- Git để clone repo.
- Docker Engine/Desktop đang chạy và Docker Compose v2 (`docker compose`).
- Internet để tải image, Python/npm packages và gọi TinyFish Agent API.
- Khóa TinyFish có quyền/hạn mức phù hợp nếu dùng nhánh phân tích URL; lấy tại
  [TinyFish API Keys](https://agent.tinyfish.ai/api-keys). Nhánh file không cần khóa.
- Các cổng host `5173`, `8000`, `8001`, `8002`, `5433`, `5678` chưa bị ứng dụng khác chiếm.
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
curl -fsS http://127.0.0.1:8000/products -H "Authorization: Bearer $PERSONAL_API_TOKEN"
```

- AI health phải báo `model_name = underthesea_bilstm_custom_vocab_v3` và 5 checkpoint.
- Lệnh `/products` cần PERSONAL_API_TOKEN tạo qua Swagger (xem AUTHENTICATION.md); thiếu xác thực trả 401.
- Với tài khoản mới, `/products` trả `{"products":[]}` là bình thường.
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

1. Đăng ký / đăng nhập ở trang chủ, chọn **Bắt đầu phân tích** (`/analyze`).
2. Dán URL sản phẩm Lazada dạng `https://www.lazada.vn/products/pdp-i3215038850-s116979513497.html`.
   Dùng link đầy đủ chứa `-i<itemId>-s<skuId>.html`; link rút gọn cần mở trong trình duyệt để lấy URL đầy đủ. Query quảng cáo được bỏ qua.
3. Nhấn phân tích và đợi request hoàn tất. Không bấm gửi liên tục trong lúc xử lý.
4. Giao diện điều hướng đến `/products/{product_db_id}/dashboard`.
5. Xem Reviews, Issues, Risk và trang History (`/history`).

Lượt phân tích có thể mất vài phút do TinyFish thu thập và backend chạy 5 fold
cho từng review mới. Đây là tác vụ online có thể phát sinh chi phí TinyFish;
nguồn có thể chặn hoặc chỉ cung cấp dữ liệu một phần. Đọc cảnh báo hoàn tất và
metadata trước khi coi tập review là đầy đủ.

Nếu muốn gọi bằng terminal, tạo khóa qua `POST /auth/api-token` trong Swagger
như [hướng dẫn xác thực](AUTHENTICATION.md#nhập-dữ-liệu), đặt vào biến PERSONAL_API_TOKEN rồi thay URL ví dụ bằng URL Lazada thực tế còn hợp lệ:

```bash
curl -sS http://127.0.0.1:8000/products/analyze \
  -H "Authorization: Bearer $PERSONAL_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.lazada.vn/products/pdp-i3215038850-s116979513497.html"}'
```

Lấy **`product_db_id`** trong response để gọi các API tiếp theo; đây là ID nội bộ,
khác `product_id`/`platform_product_id` của Lazada.

```bash
SENTIMENT_PRODUCT_DB_ID=1 # Thay bằng product_db_id thực tế
curl -fsS "http://127.0.0.1:8000/products/${SENTIMENT_PRODUCT_DB_ID}/analysis" -H "Authorization: Bearer $PERSONAL_API_TOKEN"
curl -fsS "http://127.0.0.1:8000/products/${SENTIMENT_PRODUCT_DB_ID}/histories" -H "Authorization: Bearer $PERSONAL_API_TOKEN"
curl -fsS "http://127.0.0.1:8000/products/${SENTIMENT_PRODUCT_DB_ID}/reviews?page=1&page_size=10" -H "Authorization: Bearer $PERSONAL_API_TOKEN"
```

## 6. Luồng xử lý và model AI

### 6.1. Luồng phân tích sản phẩm

1. `POST /products/analyze` nhận URL.
2. Backend gọi crawler; crawler kiểm tra URL Lazada, gọi TinyFish Agent API để
   lấy tên/review, chuẩn hóa dữ liệu, loại review rỗng/trùng và trả metadata về
   mức độ đầy đủ. Khóa API chỉ được dùng phía crawler.
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
| `products` | Chủ sở hữu, nguồn Lazada/file, URL, tên, category và thời điểm cập nhật |
| `reviews` | Nội dung gốc, rating, ngày review và trạng thái phân tích |
| `review_analysis` | Sentiment/confidence final, `model_version`, `analysis_method` |
| `issue_analysis` | Nhóm issue và keyword khớp |
| `risk_detection` | `risk_flag`, mức rủi ro và keyword |
| `analysis_history` | Snapshot số lượng/tỷ lệ sentiment và summary issue/risk theo lần phân tích |
| `review_collections` | Audit lần nhập CSV/Excel (và client API cũ), thống kê chống trùng và liên kết snapshot |
| `users`, `auth_sessions` | Tài khoản và phiên đăng nhập có thể thu hồi |
| `password_reset_tokens`, `user_api_tokens` | Token băm để reset mật khẩu và gọi API cá nhân |
| `auth_throttles` | Bộ đếm giới hạn thử đăng nhập/đăng ký/khôi phục |

Product có khóa duy nhất theo `(owner_id, platform, platform_product_id)`; Review
theo `(product_id, platform, platform_review_id)`. Sản phẩm, review và lịch sử
được giới hạn theo tài khoản đăng nhập. Đổi model/rule không tự phân tích lại dữ liệu cũ.
Tỷ lệ sentiment được tổng hợp trên review đã có analysis; có thể lệch nhẹ tổng
100% do làm tròn.

`analysis_history` lưu thống kê tổng hợp, không đóng băng đầy đủ nội dung và
kết quả của từng review ở thời điểm cũ. Các script rebuild không tự tái tạo
snapshot lịch sử. Chi tiết model/schema: [database/models.py](database/models.py).

Backend tạo bảng còn thiếu và chạy migration xác thực tự động khi khởi động,
trong một transaction có advisory lock. Migration thêm chủ sở hữu và cập nhật
unique sản phẩm/review; giữ nguyên dữ liệu. Xem [quyền dữ liệu cũ](AUTHENTICATION.md#dữ-liệu-trước-khi-có-đăng-nhập).
Những thay đổi schema khác vẫn cần migration phù hợp.

Dữ liệu PostgreSQL nằm trong named volume `postgres_data` của Compose project,
không nằm trong image backend. `docker compose down` giữ volume; `down -v` xóa
volume và dữ liệu. Không dùng `down -v` như thao tác sửa lỗi thông thường.

## 8. API

Swagger/OpenAPI khi service chạy:

- Backend: http://127.0.0.1:8000/docs
- AI: http://127.0.0.1:8001/docs
- Crawler: http://127.0.0.1:8002/docs

### Backend — cổng 8000

Các API `/products/*` và `/collections/*` cần cookie đăng nhập hoặc Bearer cá nhân.
Thiếu xác thực trả 401; sản phẩm của tài khoản khác trả 404. Luồng đăng ký,
đăng nhập và khôi phục mật khẩu: [API Authentication](AUTHENTICATION.md#api).

| Method | Endpoint | Ý nghĩa |
| --- | --- | --- |
| GET | `/` | Process backend đang chạy |
| GET | `/products` hoặc `/products/` | Danh sách sản phẩm đã lưu |
| GET | `/products/collection-config` | Nhánh thu thập URL: TinyFish Agent API |
| POST | `/products/analyze` | Body `{"url":"URL_LAZADA"}`; lấy review qua TinyFish, phân tích, ghi database |
| GET | `/collections/status` | Kiểm tra khóa nhập dữ liệu và giới hạn upload |
| POST | `/collections/reviews` | Nhận JSON cho client API cũ; cần cookie / Bearer cá nhân |
| POST | `/collections/import` | Import bytes CSV/Excel với tên sản phẩm; cần cookie / Bearer cá nhân; xem [hợp đồng API](HYBRID_COLLECTION.md#api) |
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
| POST | `/crawl` | Body `{"url":"URL_LAZADA"}`; trả platform=lazada, product ID, sku_id, tên và reviews |

Crawler mặc định gọi TinyFish Agent API qua
[`tinyfish_crawler.py`](crawler-service/tinyfish_crawler.py), không gọi
`cookie_crawler.py` và không chuyển về nguồn cũ nếu TinyFish lỗi. `GET /` cho
biết `crawler_mode=tinyfish`, `access_mode=tinyfish_api_key`. Thiếu khóa hoặc
khóa/hạn mức không hợp lệ trả lỗi cấu hình 503; giới hạn tốc độ trả 429,
lỗi kết nối/giao thức trả 502 và hết thời gian chờ trả 504. Chi tiết lỗi được
chuyển tới giao diện mà không đưa khóa API vào response/log.

Kết quả có `crawl_source=tinyfish`, `collection_provider=tinyfish`,
`crawl_status` (`FULL`/`PARTIAL`), `crawl_error` và `requires_verification` cùng
metadata về mức độ đầy đủ nếu có. Kết thúc lượt TinyFish không tự đồng nghĩa với
đã lấy đủ mọi đánh giá. Khi có review hợp lệ nhưng chưa xác minh được đầy đủ,
crawler giữ dữ liệu với `PARTIAL`; backend vẫn phân tích/lưu và giao diện hiển
thị cảnh báo. Trạng thái hoàn tất không bao gồm cam kết về review bị nguồn ẩn,
review không truy cập được hoặc review không có nội dung.

`TINYFISH_TIMEOUT_SECONDS` mặc định 600 giây, được dùng làm giới hạn thời gian
lượt thu thập TinyFish. Backend còn chạy AI/rule sau đó; mỗi lần gọi AI vẫn có
timeout 60 giây riêng cho review đó. Giữ tab phân tích mở khi xử lý nhiều review.
TinyFish có chi phí/hạn mức theo tài khoản và không bảo đảm vượt CAPTCHA hoặc
lấy mọi review. Test offline không xác nhận đã truy cập thành công Lazada thật.

Chi tiết cấu hình và giới hạn nằm trong [README crawler](crawler-service/README.md)
và [hướng dẫn URL / file](HYBRID_COLLECTION.md). `sku_id` được ghi nhận từ URL;
review trích xuất có thể thuộc toàn listing, không bảo đảm chỉ một SKU.
Ngày review được chuẩn hóa trước khi backend lưu database. Backend lưu
`platform=lazada`; các bản ghi `platform=tiki` có sẵn giữ nguyên và không bị
trùng ID với dữ liệu mới. Không cần đổi schema hay xóa volume database.

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
| `AUTH_FRONTEND_URL` | Origin website và gốc link reset; mặc định `http://localhost:5173` |
| `AUTH_COOKIE_SECURE` | `false` cho local HTTP, `true` khi triển khai HTTPS |
| `SMTP_HOST` / `SMTP_PORT` | Mailpit `mailpit:1025`, UI email thử tại `localhost:8025` |
| `TINYFISH_API_KEY` | Khóa TinyFish cho luồng URL; lấy tại [API Keys](https://agent.tinyfish.ai/api-keys), chỉ lưu cục bộ |
| `TINYFISH_TIMEOUT_SECONDS` | Thời gian chờ thu thập TinyFish, mặc định `600` giây |
| `CRAWLER_ENV_FILE` | Compose đặt `/run/duancntt/config/.env` để đọc lại khóa/timeout từ `.env` gốc mỗi lượt crawl |

File `.env.example` có sẵn cấu hình local cho Compose. Nếu đổi username,
password hoặc database, sửa đồng bộ các biến PostgreSQL và `DATABASE_URL`.
Password có ký tự đặc biệt trong URL cần URL-encode. Không commit `.env` thật.
Crawler đọc lại khóa TinyFish và timeout khi bắt đầu lượt mới; đổi hai biến này
không cần restart. Các biến service khác vẫn cần recreate container khi thay đổi.
Trong Docker, dùng `postgres:5432`; backend native trên host dùng `127.0.0.1:5433`.

`database/connection.py` tìm `database/.env` nếu file đó tồn tại, nếu không dùng
`load_dotenv()`. Biến đã có trong process được ưu tiên. Với Docker, dùng `.env`
gốc qua Compose; với native, export đúng giá trị như mục 10 để tránh hostname Docker.

Frontend gọi API qua `frontend/src/services/http.ts`, dùng cùng hostname với
website và cổng 8000. Có thể đặt VITE_API_URL khi chạy Vite/build. `BACKEND_URL`
trong `.env` không tự đổi URL frontend. Cookie được gửi bằng credentials include;
không trộn localhost và 127.0.0.1 giữa UI/API. Backend cho phép origin cấu hình
AUTH_FRONTEND_URL và hai origin local cổng 5173. Khi đổi domain phải cập nhật
AUTH_FRONTEND_URL, API URL và HTTPS/Secure cookie đồng bộ.

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
kiểm tra nhanh hệ thống đang chạy. Bộ kiểm thử offline cho chuyển đổi Lazada được hướng dẫn bên dưới.

### Kiểm thử offline crawler và backend

Sau khi build lại image theo source mới:

```bash
docker compose run --rm --no-deps crawler-service python -m unittest discover -s tests -v
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:///:memory: backend python -m unittest discover -s tests -v
```

Các test dùng phản hồi TinyFish mô phỏng và SQLite tạm; không gọi TinyFish,
Lazada/AI thật và không sử dụng database sản phẩm. Chúng kiểm tra cấu hình, URL,
chuẩn hóa review, chống trùng, dữ liệu thiếu/lỗi, timeout và tách dữ liệu theo sàn.
Các test cookie còn lại dành cho mã legacy, không phải luồng URL đang hoạt động.
Test offline thành công không chứng minh TinyFish lấy được review Lazada thật.

### Backend

```bash
curl -fsS http://127.0.0.1:8000/
curl -fsS http://127.0.0.1:8000/products -H "Authorization: Bearer $PERSONAL_API_TOKEN"
```

API gốc trả 200; `/products` cần PERSONAL_API_TOKEN tạo qua Swagger (xem AUTHENTICATION.md)
và trả danh sách riêng của tài khoản. Thiếu/sai khóa trả 401.

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

### Crawler thật — tùy chọn, cần Internet và khóa TinyFish

```bash
curl -fsS http://127.0.0.1:8002/crawl \
  -H 'Content-Type: application/json' \
  -d '{"url":"URL_SAN_PHAM_LAZADA_CON_HIEU_LUC"}'
```

Thay `URL_SAN_PHAM_LAZADA_CON_HIEU_LUC` bằng URL thật trước khi chạy, điền
`TINYFISH_API_KEY` trong `.env` và kiểm tra chi phí/hạn mức TinyFish. Lệnh này
gọi TinyFish thật để truy cập Lazada, có thể phát sinh chi phí. Kết quả phụ thuộc
nguồn và dịch vụ; kiểm tra trạng thái/cảnh báo và metadata về mức độ đầy đủ.
Không dùng test offline làm bằng chứng đã chạy thành công lệnh này.

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
# Gọi model v3 + decision layer cho các review đã lưu, không crawl Lazada
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

1. Chọn địa chỉ API mà trình duyệt người dùng truy cập được; cấu hình tập trung
   tại `frontend/src/services/http.ts` hoặc VITE_API_URL khi build.
2. Cấu hình AUTH_FRONTEND_URL theo origin frontend thực tế để CORS và link reset đúng.
3. Build frontend bằng `npm run build`; phục vụ `frontend/dist` bằng web server
   có SPA fallback về `index.html`, thay cho Vite dev server.
4. Cấu hình reverse proxy, HTTPS và timeout đủ cho request phân tích đồng bộ.
   Trang HTTPS phải gọi API HTTPS, tránh mixed content.
5. Giới hạn public ports bằng cấu hình bind/firewall; Compose hiện publish cả
   PostgreSQL, AI và crawler trên host. API sản phẩm/nhập dữ liệu yêu cầu xác thực tài khoản; xem [cấu hình HTTPS và SMTP](AUTHENTICATION.md).
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
| `/products/analyze` trả lỗi | `400`: URL sai; `503`: thiếu/sai khóa hoặc hạn mức TinyFish; `429`: giới hạn tốc độ; `502`: lỗi nguồn/dịch vụ; `504`: timeout; `500`: xem detail và log backend/AI/database |
| `/predict` trả 422 cho emoji | Bình thường với nội dung rỗng sau clean; API phân tích sản phẩm hiện bỏ qua sentiment của review đó |
| Crawl không có/thiếu review | Kiểm tra URL, cấu hình/hạn mức TinyFish, `PARTIAL`, `requires_verification` và metadata; không coi kết thúc lượt chạy là đã lấy mọi review, không fallback sang cookie |
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
- [ ] Thử một URL Lazada còn hợp lệ và kiểm tra dashboard/history sau khi phân tích.
- [ ] Nếu public domain: hoàn tất URL API, CORS, frontend static/reverse proxy và quản lý truy cập.

Không cần giao `.venv`, `node_modules` hoặc image Docker của máy cá nhân.
Weights v3 được giao bằng Git cùng source; cần bảo đảm commit trên remote thực
sự chứa đủ artifact. Bản clone thiếu weights v3 thì AI service chưa thể khởi động.
