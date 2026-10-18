# Networking: Client API & Xử Lý Giao Thức Mạng Đa Phương Thức

## 1. Thông tin tổng quan & Phiên bản
- **Công nghệ cốt lõi:** `Fetch API` chuẩn hiện đại của trình duyệt & Next.js.
- **Module quản trị:** `web/src/lib/api.ts`
- **Vai trò trong hệ thống:** Đóng gói toàn bộ các giao tiếp HTTP/RESTful giữa Web UI và Backend FastAPI: xử lý FormData upload file nhị phân (Ảnh/Audio), truyền tải query params, xử lý lỗi có cấu trúc (`ApiError`), và cấu hình địa chỉ máy chủ động.

## 2. Cài để làm gì?
- **Tải lên dữ liệu đa phương thức (Multipart/form-data):** Gửi đồng thời file ảnh nhị phân cùng chuỗi JSON tọa độ cắt (`crop_box`) và chuỗi text mô tả trong cùng một request `POST /api/search`.
- **Gửi file âm thanh (Audio WebM/WAV):** Thu âm trực tiếp qua `MediaRecorder` và đẩy file blob lên `POST /api/transcribe`.
- **Đồng bộ hóa phiên làm việc (Session Persistence):** Duy trì `session_id` xuyên suốt các lượt tìm kiếm liên tiếp (Conversational Refinement).
- **Gỡ bỏ bộ lọc tức thì (Real-time Constraint Removal):** Gửi lệnh `DELETE /api/search/{session_id}/constraint?chip_id=...` và nhận ngay danh sách sản phẩm được xếp hạng lại.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Native Fetch API**: Có sẵn trong trình duyệt và Next.js runtime, không cần thêm bundle size của Axios.
  - Hỗ trợ tốt `AbortController` phục vụ ngắt request khi người dùng nhập truy vấn mới trước khi truy vấn cũ hoàn tất.
  - Phù hợp với cơ chế TypeScript Strict Typing: Ép kiểu trả về theo các interface định nghĩa trong `web/src/types/search.ts`.
- **Phương án thay thế đã cân nhắc:**
  - *Axios*: Tiện ích nhưng thêm ~15KB bundle size và không cần thiết khi Fetch API đã hỗ trợ đầy đủ các tính năng cơ bản.
  - *React Query / SWR*: Thích hợp cho ứng dụng CRUD nhiều bảng; tuy nhiên với Single-Page Search App có state machine phức tạp (phụ thuộc vào `turn_index` và `SearchState` động), việc quản lý trực tiếp qua custom hook/handler trong `page.tsx` giúp kiểm soát chính xác thứ tự cập nhật state.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Hàm / Phương thức | Endpoint kết nối | Đường dẫn trực tiếp |
|---|---|---|---|
| `web/src/lib/api.ts` | `detectObjects(file)` | `POST /api/detect` | [api.ts](../../../../web/src/lib/api.ts#L48-L60) |
| `web/src/lib/api.ts` | `transcribeAudio(file)` | `POST /api/transcribe` | [api.ts](../../../../web/src/lib/api.ts#L61-L79) |
| `web/src/lib/api.ts` | `searchProducts(params)` | `POST /api/search` | [api.ts](../../../../web/src/lib/api.ts#L80-L114) |
| `web/src/lib/api.ts` | `deleteConstraint(sid, chip)` | `DELETE /api/search/{sid}/constraint` | [api.ts](../../../../web/src/lib/api.ts#L115-L131) |
| `web/src/lib/api.ts` | `getProductDetail(id)` | `GET /api/products/{id}` | [api.ts](../../../../web/src/lib/api.ts#L132-L149) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức kết nối thông suốt với FastAPI server tại `http://localhost:8000`.
- **Cấu hình biến môi trường:** Đọc biến `process.env.NEXT_PUBLIC_API_URL` (mặc định fallback về `http://localhost:8000`).

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bắt buộc Không Nuốt Lỗi:** Class `ApiError` bóc tách chi tiết thông điệp lỗi từ JSON response (`detail` hoặc `message`) của backend và hiển thị cảnh báo trực quan cho người dùng, tuân thủ nguyên tắc *No-Silent-Failures*.
- **Timeout & Retry:** Các tác vụ chạy model AI (như OWL-ViT hay SigLIP) có thể mất 200ms-800ms trên GPU GTX 1660 Ti, client hiển thị trạng thái loading spinner mượt mà để tránh người dùng click lặp lại.
