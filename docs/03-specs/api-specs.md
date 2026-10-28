# Đặc tả REST API

Base URL local: `http://127.0.0.1:8000`. FastAPI sinh OpenAPI tương tác tại `/docs`.

Mỗi lần gọi `/api/search` là một request độc lập. API không nhận `session_id`, không merge điều kiện từ request cũ và không có endpoint xóa constraint theo session.

## `GET /health`

Kiểm tra tiến trình backend.

```json
{
  "status": "ok",
  "service": "Interactive Multimodal Shopping Search API"
}
```

## `POST /api/detect`

Request `multipart/form-data`:

- `file`: JPEG, PNG hoặc WebP.

Response:

```json
{
  "image_hash": "...",
  "total_boxes": 1,
  "boxes": [
    {
      "box_id": "box_1",
      "label": "Pants",
      "score": 0.83,
      "box_2d": [0.1, 0.2, 0.9, 0.8],
      "polygon": null
    }
  ]
}
```

`box_2d` dùng thứ tự `[ymin, xmin, ymax, xmax]`, chuẩn hóa về khoảng 0–1.

## `POST /api/transcribe`

Request `multipart/form-data`:

- `file`: WebM, WAV, MP3, MP4, MPEG, MPGA hoặc M4A.

Response:

```json
{
  "text": "Tìm áo sơ mi trắng dưới 500 nghìn",
  "language": "vi"
}
```

Frontend gửi transcript sang `/api/search` như một request mới với `query_type=voice`.

## `POST /api/search`

Endpoint thống nhất cho text, voice, image, image + text và product reference.

Request `multipart/form-data`:

| Field | Bắt buộc | Mô tả |
|---|:---:|---|
| `query_text` | Không | Yêu cầu đầy đủ của lần tìm hiện tại |
| `image` | Không | Ảnh sản phẩm hoặc outfit |
| `crop_box` | Không | JSON `[ymin, xmin, ymax, xmax]` |
| `reference_article_id` | Không | Sản phẩm gốc cho tìm tương tự |
| `query_type` | Không | `text`, `voice` hoặc `image`; backend tự đặt `image` khi có ảnh |

Ít nhất một trong `query_text`, `image` hoặc `reference_article_id` nên có giá trị.

Response rút gọn:

```json
{
  "total_results": 12,
  "search_state": {
    "category": "Shorts",
    "gender": null,
    "color": "White",
    "min_price": null,
    "max_price": 1000000,
    "material": null,
    "style": null,
    "purpose": null,
    "exclude_colors": [],
    "exclude_materials": [],
    "reference_article_id": null
  },
  "items": [],
  "has_exact_match": true,
  "exact_items": [],
  "similar_items": [],
  "message": null,
  "response_type": "search_results",
  "query_type": "text",
  "latency_ms": 184,
  "query_id": "..."
}
```

`query_id` là ID audit trong database. Nó không phải session và không được dùng để kế thừa điều kiện.

## `GET /api/products/{product_id}`

Lấy metadata đầy đủ của một sản phẩm theo `article_id`. ID được backend chuẩn hóa về 10 ký tự trước khi truy vấn.

## Lỗi

Các exception được chuẩn hóa:

```json
{
  "error_type": "HTTPException",
  "message": "Unsupported image type...",
  "detail": null,
  "status_code": 400
}
```
