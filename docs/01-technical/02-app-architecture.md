# Kiến Trúc Ứng Dụng Tổng Thể (App Architecture)

Tài liệu này thuyết minh toàn diện cách ứng dụng **Interactive Multimodal Shopping Search Engine** được thiết kế và vận hành, cấu trúc phân tầng Monorepo, chu trình khởi động của hệ thống, và luồng giao tiếp giữa các tầng.

---

## 1. Sơ đồ Kiến trúc 5 Tầng Tổng thể

Hệ thống được tổ chức theo kiến trúc 5 tầng chuẩn mực, phân tách rõ rệt giữa giao diện người dùng, cổng giao tiếp API, cỗ máy suy luận AI, logic nghiệp vụ tìm kiếm và hạ tầng CSDL:

```mermaid
graph TB
    subgraph Tier1 ["1. Client Tier (Next.js 16 + React 19 Lookbook Studio)"]
        UI_Search["SearchBar Component<br/>(Text, Voice Recording, Image Upload)"]
        UI_Modal["ObjectSelectModal Component<br/>(Interactive HTML5 Canvas Bounding Boxes)"]
        UI_Chips["StateChipsBar Component<br/>(Active Filter Chips & Real-time Remover)"]
        UI_Grid["ProductGrid & ProductCard<br/>(Aspect 3:4 Cards, Match %, Badges)"]
        UI_Sticky["StickyRefineBar Component<br/>(Multi-turn Conversational Input at Bottom)"]
        UI_Facet["FacetSidebar Component<br/>(Price Range, Category, Gender, Color)"]
        API_Client["SearchAPIClient (src/lib/api.ts)<br/>(Native Fetch REST Wrapper)"]
    end

    subgraph Tier2 ["2. API Gateway & Controller Tier (FastAPI REST Server)"]
        R_Detect["POST /api/detect Router"]
        R_Transcribe["POST /api/transcribe Router"]
        R_Search["POST /api/search Router"]
        R_Constraint["DELETE /api/search/{session}/constraint Router"]
        R_Product["GET /api/products/{id} Router"]
        Middleware["Global Exception Handlers & CORS Middleware"]
        Static_Mount["Static Files Mount (/images & /uploads)"]
    end

    subgraph Tier3 ["3. AI & Deep Learning Inference Engines Tier"]
        Detector["ObjectDetector Engine<br/>(OWL-ViT FP16 Zero-shot Garment Detection)"]
        Transcriber["SpeechTranscriber Engine<br/>(Whisper API + Prompt Domain Fashion)"]
        Embedder["Hybrid MultimodalEmbedder Engine<br/>(OpenAI text-embedding-3-small 768-dim<br/>+ Marqo-fashionSigLIP 768-dim)"]
        LLM_Extractor["IntentExtractor Engine<br/>(GPT-4o-mini Structured JSON Outputs)"]
    end

    subgraph Tier4 ["4. Core Search & Business Services Tier"]
        Normalizer["EntityNormalizer<br/>(Phonetic & Dialect Fix, Color & Price Mapping)"]
        StateManager["StateManager<br/>(Multi-turn Session Merging, Real-time Chips Sync)"]
        Retriever["CandidateRetriever<br/>(Hybrid SQL Filter + pgvector Cosine Distance)"]
        Reranker["SoftReranker & ResultExplainer<br/>(Multi-signal Scoring & Transparent Badges)"]
        DomainModels["14 Domain Entities (TPT Model)<br/>(Customer, Product, Cart, Order, SearchQuery)"]
    end

    subgraph Tier5 ["5. Persistence & Storage Tier"]
        PG_DB[("PostgreSQL 16 Database<br/>(14 Relational Tables with 3NF Schema)")]
        PG_Vector[("pgvector Extension<br/>(HNSW Index: m=16, ef_construct=64)")]
        Local_Media[("Local Static Storage<br/>(data/images/ & data/uploads/)")]
        Mem_Cache[("In-Memory Session Cache<br/>(SESSION_STATES & Query Vectors)")]
    end

    UI_Search --> API_Client
    UI_Modal --> API_Client
    UI_Chips --> API_Client
    UI_Grid --> API_Client
    UI_Sticky --> API_Client
    UI_Facet --> API_Client

    API_Client --> R_Detect
    API_Client --> R_Transcribe
    API_Client --> R_Search
    API_Client --> R_Constraint
    API_Client --> R_Product

    R_Detect --> Detector
    R_Transcribe --> Transcriber
    R_Search --> Normalizer
    Normalizer --> LLM_Extractor
    LLM_Extractor --> StateManager
    R_Search --> Embedder
    R_Search --> StateManager
    StateManager --> Retriever
    Embedder --> Retriever
    Retriever --> PG_DB
    Retriever --> PG_Vector
    Retriever --> Reranker
    Reranker --> R_Search
    R_Constraint --> StateManager
    StateManager --> Mem_Cache
    Detector --> Local_Media
```

---

## 2. Chu Trình Khởi Động & Lifecycle Của Hệ Thống

### 2.1. Chu trình khởi động Backend (`backend/main.py`)
1. **Nạp biến môi trường**: `load_dotenv()` nạp cấu hình từ `.env` (CSDL credentials, OpenAI API Key, cờ phần cứng).
2. **Khởi tạo FastAPI Application**: Khai báo tiêu đề, mô tả tài liệu OpenAPI và phiên bản hệ thống.
3. **Cấu hình CORS Middleware**: Cho phép giao diện Next.js (`http://localhost:3000`) gọi API không bị rào cản Cross-Origin.
4. **Đăng ký Exception Handlers**: Gắn `http_exception_handler` và `general_exception_handler` đảm bảo 100% phản hồi lỗi đều tuân thủ schema `ErrorResponse`.
5. **Mount Static Folders**: Mount thư mục `data/images` vào đường dẫn `/images` và `data/uploads` vào `/uploads`.
6. **Nạp Routes**: Gắn `search_router` vào tiền tố `/api`.
7. **Khởi tạo AI Model Singletons (Lazy/Eager Loading)**:
   - Khi server nhận request đầu tiên, các Singleton `ObjectDetector.get_instance()` và `MultimodalEmbedder.get_instance()` sẽ nạp trọng số mô hình vào VRAM của GPU NVIDIA GTX 1660 Ti một lần duy nhất.

### 2.2. Chu trình khởi động Frontend (`web/src/app/page.tsx`)
1. **Khởi tạo Root Layout**: Nạp font Geist, cấu hình viewport và CSS design tokens.
2. **Kiểm tra trạng thái kết nối mạng**: Component `Header` gọi `GET /health` để xác thực server Backend đang sẵn sàng.
3. **Khởi tạo State Machine**:
   - `sessionState`: Lưu trữ trạng thái phiên tìm kiếm hiện tại (`session_id`, `turn_index`, các bộ lọc đang chọn).
   - `searchResults`: Danh sách sản phẩm kết quả, chia làm 2 phân vùng: *Exact Matches* (khớp chính xác) và *Similar Recommendations* (sản phẩm tương tự gợi ý).
   - `activeChips`: Danh sách các thẻ bộ lọc đang kích hoạt kèm nút gỡ bỏ `[✕]`.

---

## 3. Luồng Giao Tiếp Giữa Client & Backend

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as Lookbook Studio (Next.js)
    participant API as FastAPI Gateway (backend/main.py)
    participant Core as Core Search Engine
    participant DB as PostgreSQL 16 + pgvector

    User->>UI: Upload ảnh phối đồ (Outfit Image)
    UI->>API: POST /api/detect (FormData: file)
    API->>Core: ObjectDetector.detect(image_bytes)
    Core-->>API: Danh sách bounding boxes + MD5 hash
    API-->>UI: DetectResponse (boxes JSON)
    UI->>User: Hiển thị Canvas Bounding Box Modal (Top, Pants, Shoes...)
    
    User->>UI: Chọn áo Top + gõ "dưới 500k vải cotton"
    UI->>API: POST /api/search (image, crop_box, query_text, session_id)
    API->>Core: IntentExtractor.extract(query_text)
    Core-->>API: QueryIntent (max_price=500k, material="cotton")
    API->>Core: StateManager.merge_intent(state, intent)
    alt Tìm kiếm bằng Ảnh Crop (Outfit)
        API->>Core: MultimodalEmbedder.encode_image(cropped_img) [SigLIP]
        Core-->>API: Image Vector 768-dim
        API->>DB: SQL Hybrid Query (WHERE ... ORDER BY image_embedding <=> query_vector)
    else Tìm kiếm bằng Text / Voice
        API->>Core: MultimodalEmbedder.encode_text(query_text) [OpenAI text-embedding-3-small]
        Core-->>API: Text Vector 768-dim
        API->>DB: SQL Hybrid Query (WHERE ... ORDER BY text_embedding <=> query_vector)
    end
    DB-->>API: Top-50 ứng viên thô
    API->>Core: SoftReranker.rerank(candidates, state)
    Core-->>API: Danh sách sản phẩm kèm Explainable Badges
    API-->>UI: SearchResponse (JSON)
    UI->>User: Hiển thị Lưới sản phẩm thời trang + State Chips Bar
```

---

## 4. Cơ Chế Xử Lý Lỗi Tập Trung (Strict No-Silent-Failures)

Toàn bộ hệ thống tuân thủ nghiêm ngặt nguyên tắc **Không Nuốt Lỗi**:
- Mọi exception xảy ra trong quá trình xử lý (lỗi GPU Out-of-Memory, lỗi bóc tách âm thanh, lỗi cú pháp CSDL) đều được ghi log chi tiết kèm ngữ cảnh `exc_info=True`.
- Backend trả về mã lỗi HTTP chuẩn mực (400 Bad Request, 404 Not Found, 422 Validation Error, 500 Internal Error) dưới định dạng JSON:
  ```json
  {
    "error_type": "HTTPException",
    "message": "Unsupported image type: image/gif. Supported: JPEG, PNG, WebP.",
    "status_code": 400
  }
  ```
- Frontend bắt lỗi qua `ApiError` trong `src/lib/api.ts` và hiển thị Banner thông báo màu đỏ ở đầu trang để người dùng nắm rõ nguyên nhân sự cố.
