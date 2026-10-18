# OpenAI Text Embedding: Mô Hình Nhúng Văn Bản Đa Ngôn Ngữ 768 Chiều

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `openai`
- **Phiên bản:** `openai>=1.30.0`
- **Model phục vụ:** `text-embedding-3-small`
- **Tham số cấu hình đặc thù:** `dimensions=768` (ép chiều từ 1536 chuẩn về 768 chiều nhờ kỹ thuật Matryoshka Representation Learning).
- **Vai trò trong hệ thống:** Tầng Trích xuất Vector Văn bản (Text Embedding Engine), mã hóa các câu truy vấn gõ phím / giọng nói và mô tả sản phẩm thời trang thành vector 768 chiều để lưu và truy vấn trong PostgreSQL `pgvector`.

## 2. Cài để làm gì?
- **Mã hóa câu truy vấn văn bản & giọng nói (Query Text Encoding):** Nhận câu truy vấn người dùng (ví dụ: *"áo sơ mi trắng nam công sở"*, *"đầm maxi hoa nhí đi biển"*), tạo vector 768 chiều phục vụ tìm kiếm tương đồng ngữ nghĩa.
- **Mã hóa mô tả sản phẩm (Product Description Indexing):** Trong quá trình lập chỉ mục sản phẩm (`scripts/index_products.py`), kết hợp thông tin `prod_name`, `detail_desc`, `colour_group_name`, `perceived_colour_value_name` để sinh ra vector ngữ nghĩa `p.text_embedding` 768 chiều.
- **Hỗ trợ truy vấn phân tách không gian (Dual-space Separation):** Cung cấp không gian biểu diễn ngữ nghĩa văn bản độc lập với không gian thị giác của SigLIP, giúp việc tìm kiếm bằng từ khóa/giọng nói đạt độ chính xác ngữ nghĩa cao nhất.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Khả năng hiểu tiếng Việt & Đa ngôn ngữ vượt trội:** `text-embedding-3-small` được huấn luyện trên ngữ liệu đa ngôn ngữ khổng lồ, xử lý tự nhiên mối quan hệ ngữ nghĩa giữa truy vấn tiếng Việt (*"áo phao ấm"*) và mô tả sản phẩm tiếng Anh (*"quilted padded jacket with thermal lining"*).
  - **Kỹ thuật Matryoshka Representation Learning:** Cho phép cắt giảm kích thước vector từ 1536 xuống 768 chiều trực tiếp qua tham số `dimensions=768` mà bảo toàn gần như nguyên vẹn (>98%) độ chính xác của mô hình. Điều này giúp khớp hoàn hảo với cấu trúc schema `vector(768)` và chỉ mục HNSW hiện có trong PostgreSQL mà không cần migrate CSDL.
  - **Không tốn VRAM GPU:** Việc tính toán diễn ra trên đám mây của OpenAI thông qua REST API, giảm tải hoàn toàn bộ nhớ đồ họa cho máy chủ, dành 100% tài nguyên GPU (NVIDIA GTX 1660 Ti 6GB) cho mô hình thị giác SigLIP và bộ nhận diện OWL-ViT.
  - **Chi phí cực thấp:** $0.02 / 1.000.000 tokens (tương đương với hàng trăm ngàn lượt tìm kiếm chỉ tốn vài cent).
- **Phương án thay thế đã cân nhắc:**
  - *Dùng SigLIP Text Encoder*: Mặc dù SigLIP hỗ trợ cả text và ảnh trong cùng không gian nhúng, nhưng Text Encoder của SigLIP được huấn luyện trên caption ngắn bằng tiếng Anh, khả năng hiểu tiếng Việt và các ngữ cảnh tìm kiếm chi tiết còn hạn chế.
  - *text-embedding-3-large*: Độ chính xác cao hơn một chút nhưng chi phí cao gấp 6.5 lần và kích thước nén 768 chiều có tỷ lệ mất mát thông tin lớn hơn so với phiên bản `small`.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/core/embedder.py` | Class `MultimodalEmbedder`, hàm `encode_text()`, `encode_texts_batch()` với `dimensions=768` | [embedder.py](../../../../backend/core/embedder.py) |
| `backend/core/retriever.py` | Class `CandidateRetriever`, định tuyến truy vấn `col_target = "p.text_embedding"` khi `query_type in ("text", "voice")` | [retriever.py](../../../../backend/core/retriever.py) |
| `scripts/index_products.py` | Class `EmbeddingExtractor`, lập chỉ mục trường `text_embedding` theo batch 250 sản phẩm | [index_products.py](../../../../scripts/index_products.py) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức song song với SigLIP theo kiến trúc Hybrid Embedding.
- **Cơ chế Fallback 3 Tầng Siêu Bền Vững:**
  1. *Tầng 1 (Production)*: Gọi OpenAI Embeddings API (`text-embedding-3-small`, `dimensions=768`).
  2. *Tầng 2 (Local Fallback)*: Nếu không có `OPENAI_API_KEY` hoặc API timeout/network failure, tự động chuyển sang SigLIP Text Encoder cục bộ trên GPU/CPU.
  3. *Tầng 3 (Offline / Unit Test)*: Khi chạy trong môi trường kiểm thử không có GPU và không có internet, trả về deterministic normalized mock vector 768 chiều để toàn bộ 93 test cases chạy pass 100%.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Batch Processing:** Khi đánh chỉ mục dữ liệu lớn, script chia nhỏ thành các lô 250 chuỗi văn bản (`batch_size=250`) để tối ưu hóa throughput của OpenAI API và không vượt ngưỡng rate limit TPM/RPM.
- **L2 Normalization:** OpenAI API tự động chuẩn hóa vector đầu ra về độ dài đơn vị (Unit length $\|v\|_2 = 1.0$) khi chỉ định tham số `dimensions`.
- **Hiệu chuẩn ngưỡng tương đồng (Threshold Calibration):** Khoảng điểm tương đồng Cosine của `text-embedding-3-small` giữa tiếng Việt và tiếng Anh nằm trong khoảng `0.40 - 0.70`, hệ thống sử dụng ngưỡng lọc mặc định `THRESHOLD_TEXT = 0.45` (thấp hơn ngưỡng `THRESHOLD_IMAGE = 0.65` của SigLIP).
