# Speech Transcription: Chuyển Đổi Giọng Nói Sang Văn Bản (Whisper)

## 1. Thông tin tổng quan & Phiên bản
- **Công nghệ phục vụ:** OpenAI `Whisper API` (`whisper-1`) hoặc mô hình cục bộ `faster-whisper`
- **Module quản trị:** `backend/core/transcriber.py`
- **Vai trò trong hệ thống:** Tầng Xử lý Âm thanh (Audio & Speech-to-Text Engine), tiếp nhận các đoạn ghi âm truy vấn tìm kiếm bằng giọng nói tiếng Việt từ người dùng và chuyển đổi thành văn bản chính xác.

## 2. Cài để làm gì?
- Tiếp nhận file âm thanh thu âm từ trình duyệt ở các định dạng phổ biến: WebM (Chrome/Firefox), MP4/M4A (Safari/iOS), WAV, OGG.
- Nhận diện giọng nói tiếng Việt với ngữ cảnh thời trang chuyên ngành: Nhận diện chính xác các từ mượn tiếng Anh thường dùng trong thời trang (ví dụ: *sneaker, blazer, hoodie, denim, oversize, polo, cardigan, croptop*).
- Trả về chuỗi văn bản hoàn chỉnh để đưa tiếp vào pipeline tìm kiếm đa phương thức tại endpoint `POST /api/transcribe`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Mô hình Whisper của OpenAI là một trong những mô hình STT tốt nhất hiện nay cho tiếng Việt, có khả năng khử ồn môi trường tốt.
  - Sử dụng tham số `prompt="thời trang, sneaker, blazer, denim, hoodie, quần tây, áo sơ mi..."` để định hướng ngữ cảnh từ vựng, hạn chế tối đa việc phiên âm sai tên các trang phục.
  - Xử lý trên đám mây giúp tiết kiệm hoàn toàn tài nguyên CPU/GPU của máy chủ cục bộ.
- **Phương án thay thế đã cân nhắc:**
  - *Web Speech API (Trình duyệt)*: Miễn phí nhưng không ổn định, chất lượng phụ thuộc vào từng trình duyệt (Chrome tốt, Firefox/Safari kém), và không hỗ trợ prompt chuyên ngành.
  - *Google Cloud Speech-to-Text*: Đắt hơn và cấu hình xác thực service account phức tạp hơn so với OpenAI API.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/core/transcriber.py` | Class `SpeechTranscriber` (Singleton), hàm `transcribe()` | [transcriber.py](../../../../backend/core/transcriber.py) |
| `backend/routes/search_routes.py` | Endpoint `POST /api/transcribe` | [search_routes.py](../../../../backend/routes/search_routes.py#L86-L110) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức.
- **Cơ chế Fallback & Mock:**
  - Khi không có API key hoặc chạy trong môi trường test (`use_mock=True`), hàm tự động trả về chuỗi văn bản mẫu tương ứng mà không làm gián đoạn bài kiểm thử.
  - Hỗ trợ giải nén byte stream tạm ra file với hậu tố tương ứng trước khi gửi sang API.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Giới hạn dung lượng Audio:** Giới hạn file âm thanh tối đa 10MB hoặc thời lượng ghi âm dưới 15 giây (do tính chất tìm kiếm bằng giọng nói thường chỉ kéo dài từ 2 đến 5 giây).
- **Format tương thích:** Client tự động gửi kèm tên file có đuôi mở rộng chuẩn (ví dụ: `recording.webm`) để Whisper API tự động nhận diện đúng codec giải mã.
