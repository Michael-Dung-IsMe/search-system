# Pydantic: Xác Thực Dữ Liệu & Hợp Đồng Schema Nghiệp Vụ

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `pydantic`
- **Phiên bản:** `pydantic>=2.7.0` (Pydantic v2 Core Rust-based)
- **Vai trò trong hệ thống:** Định nghĩa cấu trúc hợp đồng dữ liệu nghiêm ngặt (Data Contracts), xác thực kiểu dữ liệu đầu vào (Input Validation), và tuần tự hóa đối tượng Python sang JSON (Serialization).

## 2. Cài để làm gì?
- **Đặc tả trạng thái tìm kiếm đa lượt (`SearchState`):** Lưu trữ các tiêu chí lọc (màu sắc, khoảng giá, danh mục, giới tính), danh sách vật liệu cần loại trừ (`exclude_materials`), lịch sử chip (`active_chips`), và vector truy vấn.
- **Đặc tả ý định người dùng (`QueryIntent`):** Mô hình hóa cấu trúc JSON trích xuất từ LLM OpenAI (Category, Color, Gender, MaxPrice, Modifiers, Exclusion).
- **Đặc tả hợp đồng API Request/Response:** Định nghĩa các mô hình `DetectResponse`, `TranscribeResponse`, `SearchResultItem`, `SearchResponse`, và `ErrorResponse`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Pydantic v2 được viết lại lõi bằng **Rust (`pydantic-core`)**, mang lại tốc độ xác thực và chuyển đổi JSON nhanh gấp 5 - 17 lần so với v1.
  - Tích hợp liền mạch với FastAPI: Tự động bắt lỗi sai kiểu dữ liệu và trả mã `422 Unprocessable Entity` kèm vị trí trường lỗi rõ ràng.
  - Hỗ trợ xuất trực tiếp chuẩn JSON Schema (`model_json_schema()`), phục vụ cơ chế Structured Outputs của OpenAI.
- **Phương án thay thế đã cân nhắc:**
  - *Dataclasses thuần (Python stdlib)*: Nhẹ nhưng không hỗ trợ tự động ép kiểu, kiểm tra biên số học (`ge=0`, `le=1.0`), hay tự sinh OpenAPI schema.
  - *Marshmallow*: Tốc độ chậm hơn đáng kể so với Pydantic v2 và cú pháp khai báo cồng kềnh hơn.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Mô hình dữ liệu Pydantic | Đường dẫn trực tiếp |
|---|---|---|
| `backend/schemas/state.py` | `SearchState`, `QueryIntent`, `ConstraintChip`, `SearchResultItem`, `SearchResponse` | [state.py](../../../../backend/schemas/state.py) |
| `backend/schemas/api.py` | `DetectedBox`, `DetectResponse`, `TranscribeResponse`, `ProductDetailResponse`, `ErrorResponse` | [api.py](../../../../backend/schemas/api.py) |
| `backend/routes/search_routes.py` | Gắn `response_model` cho tất cả các endpoint | [search_routes.py](../../../../backend/routes/search_routes.py) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức trên 100% các luồng dữ liệu của Backend.
- **Tuân thủ chuẩn V2:** Sử dụng các phương thức `model_dump()`, `model_validate()`, và `Field(..., description=...)` theo đúng chuẩn Pydantic v2.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bảo toàn tính bất biến (Immutability):** Khi cập nhật `SearchState` trong `StateManager.merge_intent`, phương thức `state.model_copy(deep=True)` được sử dụng để tránh lỗi tham chiếu chéo giữa các lượt tìm kiếm khác nhau.
