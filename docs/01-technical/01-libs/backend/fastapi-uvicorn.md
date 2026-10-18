# FastAPI & Uvicorn: Nền Tảng Web API Gateway & Máy Chủ ASGI

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `fastapi`, `uvicorn`
- **Phiên bản:** `fastapi>=0.111.0`, `uvicorn>=0.30.0`
- **Vai trò trong hệ thống:** Tầng Giao vận (Delivery Layer / Web API Gateway) tiếp nhận và điều phối toàn bộ các yêu cầu HTTP từ client, xử lý CORS, phân luồng upload đa phương thức, và mount thư mục tài nguyên ảnh tĩnh.

## 2. Cài để làm gì?
- Cung cấp kiến trúc Web API RESTful bất đồng bộ (Asynchronous ASGI) với hiệu năng cao.
- Điều phối các router tìm kiếm (`search_routes.py`): Tiếp nhận truy vấn đa phương thức, trích xuất multipart form-data (file ảnh nhị phân, audio blob, parameters).
- Đăng ký bộ xử lý lỗi toàn cục (*Global Exception Handlers*) chuẩn hóa mã lỗi trả về dạng `ErrorResponse` (không bao giờ nuốt lỗi).
- Mount thư mục tĩnh `data/images` và `data/uploads` phục vụ việc truy xuất ảnh sản phẩm trực tiếp từ trình duyệt qua đường dẫn `/images/...` và `/uploads/...`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Hỗ trợ bất đồng bộ `async/await` gốc giúp xử lý hàng trăm request tìm kiếm đồng thời mà không bị nghẽn I/O.
  - Tự động sinh tài liệu chuẩn **OpenAPI (Swagger UI tại `/docs` và ReDoc tại `/redoc`)**.
  - Tích hợp sâu với Pydantic v2 để validate dữ liệu đầu vào và serialize kết quả trả về tự động.
- **Phương án thay thế đã cân nhắc:**
  - *Flask*: Nhẹ nhưng xử lý async kém hơn, cần cài thêm nhiều plugin bên ngoài để validate schema và sinh OpenAPI.
  - *Django*: Quá cồng kềnh với nhiều tính năng không cần thiết (ORM quan hệ truyền thống, template engine) không phù hợp cho AI Microservice.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/main.py` | Khởi tạo instance `FastAPI()`, cấu hình CORS, Global Exception Handlers, mount static files | [main.py](../../../../backend/main.py) |
| `backend/routes/search_routes.py` | Khởi tạo `APIRouter(prefix="/api", tags=["search"])` định nghĩa 5 endpoints | [search_routes.py](../../../../backend/routes/search_routes.py) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức (Production).
- **Lệnh chạy server phát triển:**
  ```powershell
  D:\miniconda3\envs\httt-search-system\python.exe backend/main.py
  # Hoặc: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
  ```

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bắt buộc Không Nuốt Lỗi (No-Silent-Failures):** Toàn bộ lỗi chưa lường trước được bắt tại `general_exception_handler` trong `main.py`, ghi log stack trace đầy đủ bằng `logger.error(..., exc_info=True)` và trả về mã HTTP 500 kèm chi tiết lỗi `ErrorResponse`.
- **CORS Configuration:** Đã mở `allow_origins=["*"]` để hỗ trợ frontend Next.js tại `http://localhost:3000` gọi API mượt mà không gặp rào cản Cross-Origin.
