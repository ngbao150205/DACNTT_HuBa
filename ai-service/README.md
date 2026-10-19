# Sentiment inference

Hướng dẫn clone kèm model v3, cấu hình `.env`, khởi tạo database và triển khai
toàn bộ hệ thống nằm trong [README tổng dự án](../README.md).

`POST /predict` chỉ dùng bộ `models/underthesea_bilstm_custom_vocab_v3`.
Bộ này có 5 checkpoint, vocab word 4.521 token và vocab char 95 token. Predictor
nạp checkpoint, `vocab.json` và `label_encoder.pkl` cùng thư mục `_v3`;
không trộn tài nguyên của bản trước.
Luồng chạy:

1. Clean đúng pipeline huấn luyện: NFC, lowercase, rút gọn ký tự lặp từ 3
   lần trở lên thành 2, giữ chữ tiếng Việt/chữ Latin/số, chuẩn hóa khoảng trắng.
2. Nhánh word: Underthesea → gộp phủ định với token kế tiếp → `vocab.word` →
   padding/truncating `post`, độ dài 64.
3. Nhánh char: văn bản clean → `vocab.char` → padding/truncating `post`, độ dài 160.
4. Chạy `fold1.keras` đến `fold5.keras`, lấy trung bình xác suất, chọn argmax và
   giải mã bằng `label_encoder.pkl` (`Negative`, `Neutral`, `Positive`).

Không nạp/chạy model attention cũ, Keras LSTM cũ, FastText hoặc RandomForest.
AI-service chỉ trả kết quả model. Rating được nhận và trả lại, không tham gia
inference. `ensemble_predictor.py` chỉ là wrapper tương thích gọi bộ mới.
Checkpoint được nạp một lần khi khởi động, với đường dẫn tính từ file predictor.
Văn bản rỗng sau clean trả HTTP 422.

Response giữ `final.sentiment`, `final.confidence`, `final.method` để backend
hiện tại tiếp tục đọc được. `model_name` và `method` đều là
`underthesea_bilstm_custom_vocab_v3`. Backend lưu tên này vào `model_version` cho
phân tích mới. Lịch sử đã lưu không tự động được phân tích lại.

## Backend quyết định final

`backend/app/services/ai_client.py` nhận response model rồi gọi
`backend/app/services/decision_layer.py`:

- Confidence gốc **>= 0.8**: giữ nguyên sentiment/confidence model; không chạy
  các guard theo text/rating. `method = model_high_confidence`.
- Confidence gốc **< 0.8**: chạy các guard cũ (phủ định tích cực, xung đột
  rating cao/thấp, rating 3) với bộ rule tại
  `backend/app/rules/sentiment_decision_rules.json`. Không có guard khớp thì
  giữ kết quả model, `method = model_low_confidence_no_override`.

Ngưỡng được so sánh trước khi làm tròn. Chỉ có model custom vocab được gọi;
không còn so sánh kết quả với model Keras/FastText cũ. Các bộ rule issue/risk
vẫn chạy sau khi có final sentiment.

Confidence dùng để so ngưỡng là xác suất lớn nhất sau khi lấy trung bình vector
xác suất của 5 fold. Đây là điểm tin cậy của model cho từng review, khác với
accuracy được đo trên tập kiểm thử; ngưỡng 0.8 không khẳng định accuracy 80%.

Backend trả `model_result` (nhãn, confidence, probabilities gốc) và `final`
(sentiment, confidence, method sau xử lý). `raw_sentiment`, `raw_confidence`,
`rules_applied` cho biết nguồn quyết định; probabilities vẫn là của model,
không phải xác suất do rule tính. Confidence do guard đặt không phải confidence
gốc của model. Khi lưu database, backend dùng `final`, tên model vẫn được giữ.
Review chỉ emoji tiếp tục được giữ lại nhưng bỏ qua sentiment khi AI trả 422.

Kiểm tra backend sau khi hệ thống khởi động:

```sh
curl -fsS http://127.0.0.1:8000/products
```

`inference_config.json` ghi danh sách 5 fold và kiểu padding/truncating.
Do bộ `_v3` mới chưa kèm code/cấu hình tiền xử lý riêng, pipeline clean,
Underthesea, gộp phủ định và padding/truncating `post` được giữ theo code huấn
luyện đã cung cấp trước đó. Kiến trúc đầu vào và token phủ định trong vocab
mới tương thích với pipeline này. Không dùng `suspect_labels.csv` cho inference.

Runtime cố định `keras==3.13.2` theo metadata checkpoint, với TensorFlow 2.21
bản ổn định. Không dùng Keras nightly: bản nightly 3.16 của image cũ phát cảnh
báo mất masking và cho xác suất/nhãn khác trên cùng đầu vào khi kiểm thử.
Tokenizer cố định `underthesea==9.5.0`, `underthesea_core==3.3.2` theo môi trường
đã kiểm thử để tránh thay đổi tokenization khi cài lại dependency.

Sau khi sửa source, cập nhật container từ thư mục gốc dự án:

```sh
docker compose up -d --build ai-service backend
```

Kiểm tra `GET http://127.0.0.1:8001/health` để xác nhận tên model đang chạy.
Gửi một dự đoán thử:

```sh
curl -fsS http://127.0.0.1:8001/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"sản phẩm rất tốt giao hàng nhanh","rating":5}'
```

Các lệnh này kiểm tra API đang chạy; bản source hiện tại không kèm bộ unit test.
