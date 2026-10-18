# Đặc Tả Giao Diện Lập Trình Ứng Dụng (REST API Specifications)

Tài liệu này đặc tả chi tiết 5 endpoints RESTful chính của hệ thống backend FastAPI (`backend/routes/search_routes.py`), bao gồm tham số yêu cầu, định dạng dữ liệu đầu vào/đầu ra, mã lỗi HTTP và cơ chế truy vết yêu cầu (*Request Tracing*).

---

## 1. Thông Tin Máy Chủ & Cấu Trúc Lỗi Chuẩn

| Môi trường | URL cơ sở (Base URL) |
|---|---|
| **Phát triển cục bộ (Local Dev)** | `http://localhost:8000` |
| **Tài liệu trực quan tương tác** | Swagger UI: `http://localhost:8000/docs`<br/>ReDoc: `http://localhost:8000/redoc` |
| **OpenAPI Specification file** | [`api.json`](./api.json) |

### Định dạng lỗi chuẩn toàn hệ thống (`ErrorResponse`)
Mọi mã lỗi HTTP (400, 404, 422, 500) đều trả về định dạng JSON thống nhất:
```json
{
  "error_type": "HTTPException",
  "message": "Chi tiết nguyên nhân lỗi thân thiện với người dùng",
  "detail": "Stack trace hoặc log kỹ thuật bổ sung (nếu có)",
  "status_code": 400
}
```

---

## 2. Chi Tiết Các Endpoints

### 2.1. Nhận diện đối tượng trên ảnh outfit (`POST /api/detect`)
- **Mục đích**: Nhận ảnh phối đồ toàn thân từ người dùng và sử dụng mô hình OWL-ViT để phát hiện các món đồ thời trang riêng lẻ.
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  | Trường | Kiểu | Bắt buộc | Mô tả |
  |---|---|:---:|---|
  | `file` | `UploadFile` (nhị phân) | Có | File ảnh outfit định dạng JPEG, PNG hoặc WebP |
- **Response (`DetectResponse` - 200 OK)**:
  ```json
  {
    "image_hash": "4a7f9b8c1d2e3f...",
    "total_boxes": 3,
    "boxes": [
      {
        "box_id": "box_0",
        "label": "Top",
        "score": 0.94,
        "box_2d": [0.15, 0.25, 0.55, 0.75],
        "polygon": [[0.25, 0.15], [0.75, 0.15], [0.75, 0.55], [0.25, 0.55]]
      },
      {
        "box_id": "box_1",
        "label": "Pants",
        "score": 0.88,
        "box_2d": [0.52, 0.28, 0.92, 0.72],
        "polygon": [...]
      }
    ]
  }
  ```

---

### 2.2. Chuyển đổi giọng nói thành văn bản (`POST /api/transcribe`)
- **Mục đích**: Nhận đoạn ghi âm giọng nói của người dùng và chuyển đổi thành văn bản tiếng Việt qua Whisper.
- **Content-Type**: `multipart/form-data`
- **Request Body**:
  | Trường | Kiểu | Bắt buộc | Mô tả |
  |---|---|:---:|---|
  | `file` | `UploadFile` (nhị phân) | Có | File âm thanh (WebM, WAV, MP4, M4A, OGG) |
- **Response (`TranscribeResponse` - 200 OK)**:
  ```json
  {
    "text": "Tìm cho mình áo sơ mi trắng công sở nam dưới 500 ngàn",
    "language": "vi"
  }
  ```

---

### 2.3. Tìm kiếm hội thoại đa phương thức hợp nhất (`POST /api/search`)
- **Mục đích**: Endpoint trung tâm xử lý tìm kiếm kết hợp (Ảnh crop + Giọng nói/Text + Ràng buộc ngân sách/thuộc tính).
- **Content-Type**: `multipart/form-data`
- **Request Parameters / Form Data**:
  | Trường | Kiểu | Bắt buộc | Mô tả |
  |---|---|:---:|---|
  | `query_text` | `string` | Không | Câu truy vấn bằng văn bản tự nhiên |
  | `session_id` | `string` (UUID) | Không | ID phiên làm việc (nếu gửi null, server tự tạo mới) |
  | `image` | `UploadFile` | Không | File ảnh outfit đầy đủ hoặc ảnh chụp trực tiếp |
  | `crop_box` | `string` (JSON) | Không | Chuỗi JSON tọa độ cắt `[ymin, xmin, ymax, xmax]` |
  | `reference_article_id` | `string` | Không | Mã sản phẩm chọn làm gốc để tìm đồ tương tự |
  | `query_type` | `string` | Không | Loại truy vấn (`"text"`, `"image"`, `"multimodal"`) |
- **Response (`SearchResponse` - 200 OK)**:
  ```json
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "turn_index": 1,
    "total_results": 24,
    "has_exact_match": true,
    "search_state": {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "turn_index": 1,
      "gender": "Ladieswear",
      "category": "Garment Upper body",
      "color": "White",
      "max_price": 500000,
      "active_chips": [
        { "chip_id": "category:Garment Upper body", "label": "Loại: Áo", "chip_type": "category", "value": "Garment Upper body" },
        { "chip_id": "color:White", "label": "Màu: White", "chip_type": "color", "value": "White" },
        { "chip_id": "max_price:500000", "label": "Giá ≤ 500k", "chip_type": "price", "value": 500000 }
      ]
    },
    "exact_items": [
      {
        "article_id": "0123456789",
        "product_code": "0123456",
        "prod_name": "White Cotton Shirt",
        "price_vnd": 349000,
        "gender": "Ladieswear",
        "color_code": "10",
        "color_name": "White",
        "category_group": "Garment Upper body",
        "category_sub": "Shirt",
        "image_path": "images/0123456789.jpg",
        "similarity_score": 0.92,
        "badges": ["Khớp thị giác 92%", "Vải cotton", "Giá phù hợp"]
      }
    ],
    "similar_items": [],
    "message": null,
    "latency_ms": 780,
    "query_id": "c9bf9e57-1685-4c89-bafb-ff5af830be8a"
  }
  ```

---

### 2.4. Gỡ bỏ thẻ bộ lọc thời gian thực (`DELETE /api/search/{session_id}/constraint`)
- **Mục đích**: Gỡ bỏ một tiêu chí lọc khi người dùng nhấn nút `[✕]` trên thanh chip và xếp hạng lại ngay tức thì mà không cần tính lại vector ảnh.
- **Parameters**:
  - `session_id` (Path param): UUID phiên tìm kiếm hiện tại.
  - `chip_id` (Query param): Mã định danh chip cần gỡ, ví dụ `color:White` hoặc `max_price:500000`.
- **Response**: Trả về cấu trúc `SearchResponse` tương tự như `/api/search` với độ trễ siêu nhanh (<20ms).

---

### 2.5. Xem chi tiết thông tin sản phẩm (`GET /api/products/{id}`)
- **Mục đích**: Truy vấn toàn bộ metadata chi tiết của một sản phẩm theo `article_id`.
- **Path Parameter**: `id` (chuỗi 10 chữ số, ví dụ `"0108775015"`).
- **Response (`ProductDetailResponse` - 200 OK)**:
  ```json
  {
    "article_id": "0108775015",
    "product_code": "0108775",
    "prod_name": "Strap top",
    "price_vnd": 299000,
    "gender": "Ladieswear",
    "color_code": "10",
    "color_name": "White",
    "category_group": "Garment Upper body",
    "category_sub": "Top",
    "detail_desc": "Jersey top with narrow shoulder straps.",
    "image_path": "images/0108775015.jpg"
  }
  ```
- **Error**: Trả về mã `404 Not Found` nếu không tìm thấy `article_id`.
