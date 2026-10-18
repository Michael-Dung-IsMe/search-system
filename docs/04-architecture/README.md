# Quy Chuẩn Kiến Trúc Mã Nguồn & Tiêu Chuẩn Phát Triển (Architecture Guidelines)

Tài liệu này quy định cấu trúc tổ chức mã nguồn Monorepo, quy tắc chiều phụ thuộc một chiều (*Unidirectional Dependency Rule*), quy ước viết code và tiêu chuẩn kiểm thử bắt buộc cho toàn bộ thành viên trong nhóm phát triển.

---

## 1. Cấu Trúc Cây Thư Mục Monorepo

Dự án được tổ chức theo mô hình Monorepo tinh gọn, phân tách rành mạch giữa Frontend Web, Backend API & AI Engine, Tập dữ liệu, Scripts quản trị và Bộ kiểm thử:

```text
search-system/
├── backend/                     # Mã nguồn Backend (FastAPI + AI Deep Learning Engines + DB)
│   ├── main.py                  # Entrypoint khởi chạy FastAPI app, cấu hình CORS, static mounts
│   ├── routes/                  # Tầng Giao vận HTTP (search_routes.py định nghĩa 5 endpoints)
│   ├── schemas/                 # Pydantic v2 schemas (api.py, state.py)
│   ├── core/                    # Tầng Lõi AI & Thuật toán tìm kiếm:
│   │   ├── detector.py          # ObjectDetector: OWL-ViT Zero-shot Garment Detection & Crop
│   │   ├── embedder.py          # MultimodalEmbedder: Hybrid (OpenAI text-embedding-3-small + SigLIP 768-dim)
│   │   ├── extractor.py         # IntentExtractor: OpenAI gpt-4o-mini Structured JSON
│   │   ├── normalizer.py        # EntityNormalizer: Sửa phương ngữ, bảng màu & danh mục
│   │   ├── retriever.py         # CandidateRetriever: Phân vùng Exact vs Similar pgvector
│   │   ├── reranker.py          # SoftReranker & ResultExplainer: Chấm điểm mềm & Badges
│   │   ├── state_manager.py     # StateManager: Vòng đời SearchState, merge intent, chip gỡ
│   │   └── transcriber.py       # SpeechTranscriber: Whisper Speech-to-Text tiếng Việt
│   ├── domain/                  # 14 Domain Entities (TPT Model): Customer, Product, Order...
│   └── db/                      # CSDL: connection.py (Context manager pool) & schema.sql
│
├── web/                         # Mã nguồn Frontend (Next.js 16 + React 19 Lookbook Studio)
│   ├── src/
│   │   ├── app/                 # Next.js App Router: layout.tsx, page.tsx, globals.css
│   │   ├── components/          # 11 UI Components (SearchBar, ObjectSelectModal, ProductCard...)
│   │   ├── lib/                 # Client API wrapper: api.ts (Native Fetch)
│   │   └── types/               # TypeScript interfaces: search.ts
│   ├── __tests__/               # 9 test suites kiểm thử component và tích hợp
│   └── package.json             # Khai báo thư viện: React 19, Lucide, Tailwind v4, Jest
│
├── data/                        # Kho lưu trữ dữ liệu
│   ├── sample_articles.csv      # Bảng 5.000 sản phẩm H&M chọn mẫu phân tầng
│   ├── images/                  # Thư mục ảnh sản phẩm phục vụ mount tĩnh
│   └── uploads/                 # Thư mục lưu ảnh upload và ảnh crop tạm
│
├── scripts/                     # Scripts quản trị ngoại tuyến (ETL, Indexing, Benchmark)
│   ├── sample_dataset.py        # Script chọn mẫu phân tầng từ Kaggle articles.csv
│   ├── index_products.py        # Script tính vector nhúng SigLIP và insert vào PostgreSQL
│   └── benchmark_e2e.py         # Script đo đạc độ trễ toàn trình và bộ nhớ GPU
│
├── tests/                       # Bộ kiểm thử tự động toàn diện Backend (93 test cases)
│   ├── test_domain_models.py    # Kiểm thử 14 Domain Classes
│   ├── test_phase1_db_and_index.py # Kiểm thử DDL schema SQL, sampling, giá VND
│   ├── test_phase2_core_engine.py  # Kiểm thử NLU, StateManager, Retriever, Reranker
│   ├── test_phase3_api.py       # Kiểm thử 5 REST endpoints, mock DB, exception handlers
│   └── test_phase5_e2e.py       # Kiểm thử kịch bản đa phương thức tương tác toàn trình
│
├── docs/                        # Hệ thống tài liệu kỹ thuật chuẩn mực (Living Documentation)
├── docker-compose.yml           # Khởi chạy PostgreSQL 16 + pgvector container
└── requirements.txt             # Khai báo dependencies Python
```

---

## 2. Quy Tắc Chiều Phụ Thuộc Một Chiều (Unidirectional Dependency Rule)

Mọi luồng dữ liệu và tham chiếu import trong hệ thống bắt buộc phải tuân thủ nghiêm ngặt chiều phụ thuộc một chiều từ ngoài vào trong:

```text
[Web UI Components]
         │
         ▼
[web/src/lib/api.ts]
         │  (HTTP / JSON qua mạng)
         ▼
[backend/routes/ (search_routes.py)]
         │
         ▼
[backend/core/ (AI Engines & State Machine)]
         │
         ▼
[backend/domain/ & backend/schemas/]
         │
         ▼
[backend/db/ (connection.py & schema.sql)]
```

### Các điều cấm kỵ về mặt kiến trúc:
1. **Không import ngược**: Tầng `backend/db/` hoặc `backend/domain/` tuyệt đối không được import các module của tầng `backend/core/` hay `backend/routes/`.
2. **Không gọi CSDL trực tiếp từ UI**: Frontend Web tuyệt đối không bao giờ kết nối trực tiếp vào PostgreSQL; mọi thao tác đều phải đi qua các REST endpoints của Backend.
3. **Cô lập logic AI**: Tầng `routes/` chỉ đóng vai trò phân tích request parameters, gọi hàm nghiệp vụ trong `core/` và đóng gói response, không viết thuật toán tính điểm vector hay xử lý ảnh trực tiếp trong hàm route.

---

## 3. Tiêu Chuẩn Kiểm Thử Bắt Buộc (Testing Standards)

1. **Quy chuẩn Tỷ lệ Bao phủ (Code Coverage) > 80%**:
   - Mọi module mới thêm vào `backend/core/` hoặc `backend/routes/` đều phải đi kèm unit test tương ứng trong `tests/`.
   - Lệnh kiểm tra độ bao phủ:
     ```powershell
     D:\miniconda3\envs\httt-search-system\python.exe -m pytest --cov=backend tests/
     ```
2. **Quy tắc Không Nuốt Lỗi (No-Silent-Failures)**:
   - Nghiêm cấm sử dụng các khối bắt lỗi rỗng `try: ... except: pass` trong Python hoặc `try { ... } catch {}` trong TypeScript.
   - Mọi lỗi ngoại lệ phải được ghi log kèm thông tin ngữ cảnh (`logger.error(..., exc_info=True)`) hoặc re-raise để tầng trên xử lý.
3. **Kiểm thử Hợp đồng & Biên Dữ liệu (Contract & Boundary Testing)**:
   - Luôn kiểm thử các trường hợp dữ liệu rỗng (empty image, empty query string), dữ liệu âm (giá tiền âm), ký tự đặc biệt, và định dạng file không hỗ trợ để đảm bảo hệ thống không bao giờ bị crash đột ngột.

---

## 4. Hướng Dẫn Thêm Tính Năng Mới Cho Thành Viên

Khi muốn thêm một Endpoint mới hoặc một Model AI mới:
1. **Bước 1 (Schema)**: Định nghĩa hợp đồng dữ liệu trong `backend/schemas/` hoặc `web/src/types/`.
2. **Bước 2 (Core Logic)**: Viết hàm xử lý thuật toán thuần trong `backend/core/`.
3. **Bước 3 (Test)**: Viết test case kiểm thử trong `tests/` và chạy pytest đảm bảo pass.
4. **Bước 4 (Route)**: Đăng ký router endpoint trong `backend/routes/` và gắn `response_model`.
5. **Bước 5 (Frontend)**: Bổ sung hàm gọi tương ứng trong `web/src/lib/api.ts` và gắn vào component UI.
6. **Bước 6 (Documentation)**: Cập nhật tài liệu tương ứng trong `docs/` để đảm bảo tài liệu luôn song hành với mã nguồn thực tế.
