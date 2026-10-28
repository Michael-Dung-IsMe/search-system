# Speech Transcription: Chuyển Đổi Giọng Nói Sang Văn Bản

## 1. Thông tin tổng quan & Phiên bản
- **Công nghệ phục vụ:** OpenAI Audio Transcriptions API với `gpt-transcribe`
- **Module quản trị:** `backend/core/transcriber.py`
- **Vai trò trong hệ thống:** Tầng Xử lý Âm thanh (Audio & Speech-to-Text Engine), tiếp nhận các đoạn ghi âm truy vấn tìm kiếm bằng giọng nói tiếng Việt từ người dùng và chuyển đổi thành văn bản chính xác.

## 2. Cài để làm gì?
- Tiếp nhận file âm thanh thu âm từ trình duyệt ở các định dạng phổ biến: WebM (Chrome/Firefox), MP4/M4A (Safari/iOS), WAV, MP3, MPEG và MPGA.
- Nhận diện tiếng Việt bằng gợi ý ngôn ngữ `languages=["vi"]`; không dùng danh sách keyword hoặc rule từ vựng cố định.
- Trả về chuỗi văn bản hoàn chỉnh để đưa tiếp vào pipeline tìm kiếm đa phương thức tại endpoint `POST /api/transcribe`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - `gpt-transcribe` là model OpenAI khuyến nghị cho file ghi âm hoàn chỉnh.
  - Model tự nhận dạng nội dung lời nói; hệ thống chỉ cung cấp ngôn ngữ dự kiến là tiếng Việt.
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
- **Cơ chế lỗi và Mock:**
  - Môi trường chạy thật yêu cầu `OPENAI_API_KEY`. Nếu thiếu key hoặc API thất bại, endpoint trả lỗi thay vì transcript giả.
  - Chuỗi mock chỉ được sử dụng khi bài kiểm thử chủ động khởi tạo `use_mock=True`.
  - Byte stream được gửi trực tiếp lên API cùng tên file và phần mở rộng tương ứng.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Format tương thích:** WebM, WAV, MP3, MP4, MPEG, MPGA và M4A.
- **Ngôn ngữ:** Endpoint hiện cố định tiếng Việt bằng `languages=["vi"]`.
