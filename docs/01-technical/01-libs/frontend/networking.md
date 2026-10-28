# Networking giữa Next.js và FastAPI

`web/src/lib/api.ts` dùng Fetch API và `FormData` cho bốn thao tác:

| Hàm | Endpoint |
|---|---|
| `detectObjects(file)` | `POST /api/detect` |
| `transcribeAudio(file)` | `POST /api/transcribe` |
| `searchProducts(params)` | `POST /api/search` |
| `getProductDetail(id)` | `GET /api/products/{id}` |

`searchProducts()` có thể gửi text, image, crop box, product reference và query type trong cùng request. Không có session persistence. Khi facet thay đổi, `page.tsx` tạo một query chứa toàn bộ facet đang chọn rồi gọi `searchProducts()` lại.

Base URL đọc từ `NEXT_PUBLIC_API_URL`, mặc định `http://localhost:8000`. `ApiError` chuẩn hóa lỗi HTTP dựa trên `detail` hoặc `message` trong JSON response.
