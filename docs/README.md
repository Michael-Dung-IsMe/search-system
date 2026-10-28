# Hệ Thống Tài Liệu Kỹ Thuật (System Documentation)
## Interactive Multimodal Shopping Search Engine
### Môn học: Phân tích & Thiết kế Hệ thống Thông tin (PTTK-HTTT) — Nhóm 6

Tài liệu này là **trang chỉ mục gốc (Table of Contents)** dẫn dắt toàn bộ hệ thống tài liệu kỹ thuật chuẩn mực (*Living Documentation*) của dự án. Mọi thông tin trong bộ tài liệu này đều được **đối soát trực tiếp từ mã nguồn thực tế đang hoạt động** (`backend/`, `web/`, `scripts/`, `tests/`).

---

## 1. Bối Cảnh Hệ Thống & Cấu Hình Phần Cứng

- **Mục tiêu đề án:** Xây dựng hệ thống tìm kiếm thời trang đa phương thức theo từng request độc lập (Văn bản tự nhiên, Giọng nói tiếng Việt, Hình ảnh và Ảnh + Văn bản), nhận diện món đồ theo vùng chọn (*OWL-ViT*), bóc tách ý định bằng LLM (*GPT-4o-mini*), và xếp hạng sản phẩm đa tín hiệu kết hợp vector tương đồng (*OpenAI text-embedding-3-small + Marqo-fashionSigLIP 768-dim + PostgreSQL 16 pgvector*).
- **Cấu hình phần cứng tối ưu hóa thực tế:**
  - **CPU:** Intel Core i7-9750H (6 cores, 12 threads)
  - **GPU:** NVIDIA GeForce GTX 1660 Ti (6.0 GB VRAM, CUDA 13.2)
  - **RAM:** 16 GB DDR4
  - **Tập dữ liệu:** 5.000 sản phẩm thời trang H&M chọn mẫu phân tầng (60% Nữ, 40% Nam, 6 nhóm danh mục trang phục).

---

## 2. Mục Lục Hệ Thống Tài Liệu

Bộ tài liệu được tổ chức thành 4 phân khu chuyên biệt:

```text
docs/
├── 01-technical/                                
│   ├── 01-libs/
│   │   ├── frontend/
│   │   └── backend/
│   ├── 02-app-architecture.md
│   ├── 03-multimodal-pipeline.md
│   ├── 05-hardware-memory-optimization.md
│   └── benchmark-results.json
│
├── 02-product/
│   ├── overview.md
│   ├── user-flows.md
│   └── dataset-spec.md
│
├── 03-specs/                                   
│   ├── api-specs.md
│   ├── api.json
│   └── database-schema.md
│
└── 04-architecture/                             
    └── README.md
```

---

## 3. Bảng Tra Cứu Nhanh Tài Liệu Thành Phần

### 📁 `01-technical/` — Kỹ thuật & Thư viện

#### Thư viện Web Frontend (`01-technical/01-libs/frontend/`)
| Tài liệu | Thư viện / Công nghệ | Vai trò trong giao diện |
|---|---|---|
| [nextjs.md](01-technical/01-libs/frontend/nextjs.md) | `next` 16.4 | Framework App Router, Turbopack, SSR/CSR, routing |
| [react.md](01-technical/01-libs/frontend/react.md) | `react` 19.3 | Quản lý state phản ứng, DOM Canvas ref, lifecycle |
| [styling-tailwind.md](01-technical/01-libs/frontend/styling-tailwind.md) | `tailwindcss` v4 | Design tokens, utility classes, grid sản phẩm đáp ứng |
| [icons.md](01-technical/01-libs/frontend/icons.md) | `lucide-react` 1.56 | Hệ thống biểu tượng vector SVG, visual cues |
| [canvas-crop.md](01-technical/01-libs/frontend/canvas-crop.md) | HTML5 Canvas API | Bounding box tương tác, polygon viền, client crop |
| [networking.md](01-technical/01-libs/frontend/networking.md) | Fetch API / `api.ts` | Giao tiếp REST, multipart FormData, xử lý lỗi `ApiError` |
| [testing.md](01-technical/01-libs/frontend/testing.md) | Jest 30 & RTL 16 | Kiểm thử component UI, mô phỏng user events, jsdom |

#### Thư viện Backend & AI Engine (`01-technical/01-libs/backend/`)
| Tài liệu | Thư viện / Công nghệ | Vai trò trong máy chủ & AI |
|---|---|---|
| [fastapi-uvicorn.md](01-technical/01-libs/backend/fastapi-uvicorn.md) | `fastapi`, `uvicorn` | ASGI Web API Gateway, CORS, static mounts |
| [pydantic-validation.md](01-technical/01-libs/backend/pydantic-validation.md) | `pydantic` v2.7 | Schema nghiêm ngặt (`SearchState`, `QueryIntent`) |
| [database-drivers.md](01-technical/01-libs/backend/database-drivers.md) | `psycopg` 3.1 | Connection pool, parameterized SQL, context manager |
| [pgvector.md](01-technical/01-libs/backend/pgvector.md) | `pgvector` 0.3 | Vector DB, toán tử `<=>` cosine, chỉ mục HNSW |
| [open-clip-siglip.md](01-technical/01-libs/backend/open-clip-siglip.md) | `open_clip_torch`, SigLIP | Fashion visual embedding 768-dim cho ảnh catalog và crop |
| [openai-embeddings.md](01-technical/01-libs/backend/openai-embeddings.md) | OpenAI API (`text-embedding-3-small`) | Text & Voice embedding 768-dim (dimensions=768) |
| [owl-vit-detector.md](01-technical/01-libs/backend/owl-vit-detector.md) | `transformers`, OWL-ViT | Zero-shot object detection trang phục từ ảnh outfit |
| [intent-llm.md](01-technical/01-libs/backend/intent-llm.md) | `openai` (gpt-4o-mini) | Structured JSON outputs, bóc tách ý định & phủ định |
| [speech-transcription.md](01-technical/01-libs/backend/speech-transcription.md) | Whisper API | Speech-to-Text tiếng Việt chuyên ngành thời trang |
| [data-processing.md](01-technical/01-libs/backend/data-processing.md) | `pandas`, `numpy` | Stratified sampling 5.000 mẫu H&M, vector math |
| [testing-qa.md](01-technical/01-libs/backend/testing-qa.md) | `pytest`, `pytest-cov` | 93 test cases, code coverage > 80%, contract test |
| [env-config.md](01-technical/01-libs/backend/env-config.md) | `python-dotenv` | Quản lý biến môi trường, bảo mật API keys |

#### Tài liệu Kiến trúc Lõi (`01-technical/`)
- [02-app-architecture.md](01-technical/02-app-architecture.md): Sơ đồ kiến trúc 5 tầng, chu trình khởi động hệ thống và luồng giao tiếp.
- [03-multimodal-pipeline.md](01-technical/03-multimodal-pipeline.md): Luồng xử lý đa phương thức 6 bước và công thức tái xếp hạng đa tín hiệu.
- [05-hardware-memory-optimization.md](01-technical/05-hardware-memory-optimization.md): Chiến lược tối ưu VRAM trên GTX 1660 Ti (6GB), chế độ FP16 và benchmark thực nghiệm.

---

### 📁 `02-product/` — Sản phẩm & Nghiệp vụ
- [overview.md](02-product/overview.md): Nghiệp vụ tìm kiếm thời trang đa phương thức và ma trận đối soát 11 UI components.
- [user-flows.md](02-product/user-flows.md): 4 kịch bản người dùng cốt lõi (Ảnh outfit, Giọng nói, Tinh chỉnh đa lượt, Gỡ bộ lọc).
- [dataset-spec.md](02-product/dataset-spec.md): Bộ dữ liệu đại diện 5.000 sản phẩm H&M và quy chuẩn giá VND.

---

### 📁 `03-specs/` — Đặc tả Kỹ thuật & CSDL
- [api-specs.md](03-specs/api-specs.md): Đặc tả chi tiết 5 REST endpoints, request/response payload và error handling.
- [api.json](03-specs/api.json): File OpenAPI 3.1 specification sinh trực tiếp từ FastAPI application.
- [database-schema.md](03-specs/database-schema.md): Sơ đồ ERD CSDL 14 bảng chuẩn hóa 3NF, mô hình Table-Per-Type (TPT) và cấu hình HNSW.

---

### 📁 `04-architecture/` — Quy chuẩn Mã nguồn
- [README.md](04-architecture/README.md): Cấu trúc Monorepo (`backend/` + `web/`), quy tắc luồng phụ thuộc một chiều và tiêu chuẩn kiểm thử bắt buộc (Coverage > 80%).

---

### 📖 Sổ Tay Vận Hành (Operations Runbook)
- [runbook.md](runbook.md): Hướng dẫn chi tiết từng bước khởi chạy, kiểm thử và xử lý sự cố cho **Máy hiện tại** và **Thiết bị mới**.


