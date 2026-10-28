# Pydantic và hợp đồng dữ liệu

Pydantic định nghĩa JSON contract giữa core logic, FastAPI và frontend.

## Các schema chính

| File | Schema |
|---|---|
| `backend/schemas/state.py` | `QueryIntent`, `SearchState`, `SearchResultItem`, `SearchResponse` |
| `backend/schemas/api.py` | `DetectedBox`, `DetectResponse`, `TranscribeResponse`, `ProductDetailResponse`, `ErrorResponse` |

`SearchState` chỉ chứa các điều kiện của một request hiện tại: category, gender, color, price, material, style, purpose, exclusions và optional product reference. Nó không có session, turn index hoặc constraint chips.

`QueryIntent` là schema Structured Output cho LLM. `SearchResponse` được phản chiếu sang `web/src/types/search.ts`; khi đổi Pydantic schema cần cập nhật TypeScript contract tương ứng.

FastAPI dùng các model này làm `response_model`, tự sinh OpenAPI và trả lỗi validation có cấu trúc.
