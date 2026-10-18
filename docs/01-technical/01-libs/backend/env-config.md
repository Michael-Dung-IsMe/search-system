# Environment Configuration: Python-dotenv & Bảo Mật Khóa API

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `python-dotenv`
- **Phiên bản:** `python-dotenv>=1.0.0`
- **Vai trò trong hệ thống:** Tầng Cấu hình Môi trường (Configuration Management), đọc và nạp các biến môi trường từ file `.env` vào `os.environ`, đảm bảo nguyên tắc bảo mật và tách bạch giữa mã nguồn và cấu hình máy chủ.

## 2. Cài để làm gì?
- Quản lý thông tin kết nối CSDL PostgreSQL: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`.
- Quản lý khóa bí mật dịch vụ AI: `OPENAI_API_KEY`, `GEMINI_API_KEY`.
- Cấu hình cờ hiệu năng phần cứng: `USE_CUDA`, `BATCH_SIZE`, `CONFIDENCE_THRESHOLD`.
- Ngăn chặn hoàn toàn việc rò rỉ khóa bí mật (API Keys / Credentials) lên Git repository thông qua cơ chế `.env` kết hợp `.gitignore`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Tiêu chuẩn công nghiệp theo nguyên tắc Twelve-Factor App (Cấu hình lưu trong môi trường).
  - Tự động nạp khi ứng dụng hoặc các script offline khởi động qua lệnh `load_dotenv()`.
  - Nhẹ nhàng, không phụ thuộc vào các dịch vụ quản lý bí mật đám mây cồng kềnh trong môi trường phát triển cục bộ.
- **Phương án thay thế đã cân nhắc:**
  - *Hardcode trong file cấu hình (`config.py`)*: Cực kỳ nguy hiểm, dễ vô tình commit khóa bí mật lên repository công khai.
  - *Pydantic-Settings (`BaseSettings`)*: Rất tốt nhưng `python-dotenv` trực tiếp gọn nhẹ hơn cho các script nhỏ trong `scripts/`.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Biến môi trường sử dụng | Đường dẫn trực tiếp |
|---|---|---|
| `.env.example` | Mẫu khai báo các biến môi trường bắt buộc của dự án | [.env.example](../../../../.env.example) |
| `backend/db/connection.py` | Đọc `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | [connection.py](../../../../backend/db/connection.py#L15-L25) |
| `backend/core/extractor.py` | Nạp `OPENAI_API_KEY` và `GEMINI_API_KEY` | [extractor.py](../../../../backend/core/extractor.py#L15-L22) |
| `docker-compose.yml` | Đọc cấu hình cổng và mật khẩu container PostgreSQL | [docker-compose.yml](../../../../docker-compose.yml#L6-L12) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức. File mẫu `.env.example` được commit an toàn trên git, file thật `.env` được bảo vệ trong `.gitignore`.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bảo mật Tuyệt đối (Security Rule):** Tuyệt đối không bao giờ commit file `.env` chứa khóa thật lên Git. Nếu phát hiện khóa bị lộ, phải thu hồi (revoke) ngay lập tức trên trang quản trị nhà cung cấp.
- **Fallback Mặc định:** Với các thông số kết nối cục bộ (như `POSTGRES_PORT=5434`), hệ thống có giá trị mặc định hợp lý để các bài test có thể chạy mượt mà ngay cả khi file `.env` chưa được tạo.
