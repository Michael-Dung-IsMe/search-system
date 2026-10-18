# Testing & QA: Pytest, Httpx & Tiêu Chuẩn Kiểm Thử Backend

## 1. Thông tin tổng quan & Phiên bản
- **Tên packages:** `pytest`, `pytest-cov`, `pytest-asyncio`, `httpx`
- **Phiên bản:** `pytest>=8.2.0`, `pytest-cov>=5.0.0`, `pytest-asyncio>=0.23.0`, `httpx>=0.27.0`
- **Vai trò trong hệ thống:** Bộ công cụ kiểm thử tự động toàn diện cho tầng Backend, bảo vệ chất lượng mã nguồn thông qua kiểm thử đơn vị (Unit Tests), kiểm thử hợp đồng CSDL (Contract Tests), kiểm thử API tích hợp (Integration Tests) và kịch bản thực tế xuyên suốt (E2E Tests).

## 2. Cài để làm gì?
- Kiểm thử toàn diện 14 Domain Classes trong `backend/domain/models.py`.
- Kiểm thử thuật toán phân tầng (Phase 1: Stratified Sampling & Vector Ingestion).
- Kiểm thử các cỗ máy lõi AI (Phase 2: EntityNormalizer, IntentExtractor, StateManager, CandidateRetriever, SoftReranker).
- Kiểm thử các Endpoint API qua `fastapi.testclient.TestClient` (Phase 3: `/api/detect`, `/api/transcribe`, `/api/search`, `/api/search/{sid}/constraint`, `/api/products/{id}`).
- Kiểm thử toàn trình End-to-End đa lượt tương tác (Phase 5: từ ảnh outfit $\to$ trích xuất hộp $\to$ crop $\to$ refine bằng text/giọng nói $\to$ gỡ chip).
- Đo lường và thực thi quy chuẩn bắt buộc: **Tỷ lệ bao phủ mã nguồn (Code Coverage) > 80%**.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Pytest 8.x**: Hệ thống Fixtures cực kỳ mạnh mẽ, quản lý mock context và tài nguyên kiểm thử an toàn (`@pytest.fixture(scope="module")`).
  - **Httpx & TestClient**: Mô phỏng gọi API qua bộ nhớ mà không cần mở socket mạng thực tế, tốc độ chạy 93 test cases chỉ mất ~45 giây.
  - Báo cáo chi tiết vị trí sai khác (`assertion rewriting`) rõ ràng, dễ chẩn đoán lỗi.
- **Phương án thay thế đã cân nhắc:**
  - *Unittest (Python stdlib)*: Quá nhiều boilerplate code (phải tạo class kế thừa `unittest.TestCase`), cú pháp assertion rườm rà.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn kiểm thử | Phạm vi kiểm thử | Số lượng test cases | Đường dẫn trực tiếp |
|---|---|:---:|---|
| `tests/test_domain_models.py` | 14 Domain Classes (Customer, Product, Order, SearchQuery...) | 5 | [test_domain_models.py](../../../../tests/test_domain_models.py) |
| `tests/test_phase1_db_and_index.py` | Stratified Sampling, Giá VND, Schema SQL DDL contracts | 29 | [test_phase1_db_and_index.py](../../../../tests/test_phase1_db_and_index.py) |
| `tests/test_phase2_core_engine.py` | Normalizer, IntentExtractor, StateManager, Retriever, Reranker | 23 | [test_phase2_core_engine.py](../../../../tests/test_phase2_core_engine.py) |
| `tests/test_phase3_api.py` | 5 REST endpoints, Exception Handlers, Mock DB, File uploads | 29 | [test_phase3_api.py](../../../../tests/test_phase3_api.py) |
| `tests/test_phase5_e2e.py` | Kịch bản luồng đa phương thức tương tác 5 lượt hoàn chỉnh | 7 | [test_phase5_e2e.py](../../../../tests/test_phase5_e2e.py) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Toàn bộ **93/93 test cases** đều đang PASS 100%.
- **Lệnh thực thi toàn bộ test suite:**
  ```powershell
  D:\miniconda3\envs\httt-search-system\python.exe -m pytest tests/
  ```
- **Lệnh kiểm tra tỷ lệ bao phủ mã nguồn (Coverage):**
  ```powershell
  D:\miniconda3\envs\httt-search-system\python.exe -m pytest --cov=backend tests/
  ```

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Nguyên tắc Không Bỏ Qua Ngoại Lệ (No Silent Failure):** Toàn bộ test cases đều xác thực chặt chẽ rằng khi gặp lỗi biên hoặc dữ liệu rác, hệ thống phải raise đúng ngoại lệ mong đợi (`pytest.raises(ValueError)`) hoặc trả về mã lỗi HTTP tương ứng (400, 404, 422).
- **Isolation:** Các test của `test_phase3_api.py` sử dụng `unittest.mock.patch` để cô lập CSDL và AI models, đảm bảo test suite chạy độc lập không phụ thuộc vào hạ tầng bên ngoài.
