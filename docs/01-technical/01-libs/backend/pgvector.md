# pgvector: Tìm Kiếm Vector Tương Đồng Cao Chiều Trong PostgreSQL

## 1. Thông tin tổng quan & Phiên bản
- **Tên extension / package:** `pgvector` (Extension CSDL) & `pgvector-python`
- **Phiên bản:** `pgvector>=0.3.0` (chạy trên PostgreSQL 16)
- **Vai trò trong hệ thống:** Tầng Lưu trữ & Tìm kiếm Vector tương đồng (Vector Database Engine), lưu trữ các vector đặc trưng 768 chiều của sản phẩm và thực hiện truy vấn Approximate Nearest Neighbors (ANN) với độ trễ cực thấp (<15ms).

## 2. Cài để làm gì?
- Lưu trữ 2 trường vector trực tiếp trên bảng `product`:
  - `image_embedding vector(768)`: Vector thị giác trích xuất từ ảnh sản phẩm qua `Marqo/marqo-fashionSigLIP`.
  - `text_embedding vector(768)`: Vector ngữ nghĩa trích xuất từ mô tả sản phẩm qua OpenAI `text-embedding-3-small` (dimensions=768).
- Tính khoảng cách tương đồng góc Cosine giữa vector truy vấn của người dùng (từ ảnh crop hoặc text prompt) với 5.000 sản phẩm thời trang qua toán tử `<=>`:
  $$\text{Cosine Distance}(u, v) = 1 - \frac{u \cdot v}{\|u\|_2 \|v\|_2}$$
  $$\text{Similarity Score} = 1 - \text{Cosine Distance}$$
- Kết hợp hoàn hảo trong một câu lệnh duy nhất: vừa lọc thuộc tính quan hệ (SQL WHERE giá, màu sắc, danh mục) vừa tính độ tương đồng vector (Hybrid Search).

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Tất cả trong một (ACID + Vector)**: Không cần duy trì thêm một hệ thống Vector DB rời rạc (như Milvus hay Pinecone). Dữ liệu quan hệ, đơn hàng, người dùng và vector sống chung một CSDL duy nhất.
  - **Hỗ trợ chỉ mục HNSW (Hierarchical Navigable Small World)**: Cho phép tìm kiếm ANN với Recall@10 > 98% và độ trễ chỉ 5ms - 15ms trên tập 5.000 sản phẩm.
  - Hoàn toàn mã nguồn mở, triển khai nhẹ nhàng qua Docker image `pgvector/pgvector:pg16`.
- **Phương án thay thế đã cân nhắc:**
  - *ChromaDB / Qdrant*: Phải quản lý 2 database riêng biệt, khó duy trì tính toàn vẹn tham chiếu khóa ngoại giữa vector ID và bảng `product`.
  - *Faiss*: Chỉ lưu trên RAM hoặc file nhị phân, không hỗ trợ giao dịch ACID hay lọc kết hợp SQL linh hoạt.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/db/schema.sql` | Khai báo `CREATE EXTENSION IF NOT EXISTS "vector";`, định nghĩa cột `vector(768)` và chỉ mục HNSW | [schema.sql](../../../../backend/db/schema.sql#L5-L42) |
| `backend/db/connection.py` | Kích hoạt `pgvector.psycopg.register_vector(conn)` để chuyển đổi kiểu dữ liệu | [connection.py](../../../../backend/db/connection.py#L30-L36) |
| `backend/core/retriever.py` | Câu lệnh SQL tính khoảng cách vector qua toán tử `<=>` | [retriever.py](../../../../backend/core/retriever.py#L90-L135) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức trên Docker container `fashion_search_postgres`.
- **Cấu hình chỉ mục HNSW trong schema.sql:**
  ```sql
  CREATE INDEX IF NOT EXISTS idx_product_image_vector 
  ON product USING hnsw (image_embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Chuẩn hóa Vector (L2 Normalization):** Toàn bộ vector sinh ra từ mô hình SigLIP và OpenAI `text-embedding-3-small` trước khi lưu vào CSDL hoặc trước khi truy vấn đều được chuẩn hóa độ dài $\|v\|_2 = 1.0$. Khi đó khoảng cách Cosine tương đương với tích vô hướng (Dot Product), giúp chỉ mục HNSW tính toán nhanh hơn 2x.
- **Tham số `ef_search`:** Trong phiên làm việc, có thể thiết lập `SET hnsw.ef_search = 40;` để cân bằng tối ưu giữa độ chính xác truy hồi (Recall) và thời gian thực thi (Latency).
