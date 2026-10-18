# Database Drivers: Psycopg 3 & Quản Lý Kết Nối PostgreSQL 16

## 1. Thông tin tổng quan & Phiên bản
- **Tên packages:** `psycopg[binary]`, `sqlalchemy`
- **Phiên bản:** `psycopg[binary]>=3.1.0`, `sqlalchemy>=2.0.0`
- **Vai trò trong hệ thống:** Tầng Kết nối và Giao tiếp CSDL (Database Driver), quản lý kết nối an toàn, thực thi truy vấn tham số hóa (Parameterized SQL), và hỗ trợ kiểu dữ liệu nhị phân pgvector.

## 2. Cài để làm gì?
- Quản lý vòng đời kết nối an toàn với PostgreSQL 16 thông qua mẫu thiết kế **Context Manager (`with get_db_connection() as conn:`)**.
- Thực thi các câu lệnh truy vấn lọc cứng (SQL Hard Constraints: lọc theo `gender`, `price_vnd`, `color_code`, `category_id`).
- Hỗ trợ cú pháp truy vấn tính khoảng cách vector cosine trực tiếp trên bảng `product`:
  ```sql
  SELECT article_id, prod_name, price_vnd,
         (image_embedding <=> %s::vector) AS distance
  FROM product
  WHERE price_vnd <= %s
  ORDER BY distance ASC
  LIMIT 50;
  ```
- Lưu nhật ký kiểm toán (Audit Trail) các lượt tìm kiếm vào bảng `search_query`, `text_query`, `image_query`, và `search_result`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Psycopg 3 (psycopg[binary])**: Là phiên bản hiện đại được viết lại hoàn toàn, tối ưu hóa giao thức PostgreSQL v3, hỗ trợ Python types trực tiếp (UUID, JSONB, Vector), và tốc độ xử lý nhanh hơn Psycopg 2 cũ.
  - Hỗ trợ tốt kiểu dữ liệu `vector` thông qua việc tự động nạp extension `pgvector.psycopg`.
  - Không gặp lỗi kết nối treo (hanging connection) nhờ cấu hình context manager tự động commit/rollback.
- **Phương án thay thế đã cân nhắc:**
  - *Psycopg2-binary*: Đã cũ, gặp nhiều hạn chế khi thao tác với các kiểu dữ liệu mảng và vector kích thước lớn (768 chiều).
  - *Asyncpg*: Rất nhanh nhưng khó debug hơn và tương thích thư viện pgvector phức tạp hơn khi chạy các script offline.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/db/connection.py` | Hàm `get_db_connection()` khởi tạo kết nối kèm đăng ký `register_vector` | [connection.py](../../../../backend/db/connection.py) |
| `backend/core/retriever.py` | Thực thi truy vấn phân vùng (Exact match vs Similar recommendation) | [retriever.py](../../../../backend/core/retriever.py) |
| `backend/core/state_manager.py` | Hàm `persist_turn()` lưu vết lịch sử truy vấn vào PostgreSQL | [state_manager.py](../../../../backend/core/state_manager.py) |
| `scripts/index_products.py` | Batch insert 5.000 vector embeddings vào bảng `product` | [index_products.py](../../../../scripts/index_products.py) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức kết nối PostgreSQL 16 qua cổng `5434` (cấu hình trong `docker-compose.yml` và `.env`).
- **Cơ chế Fallback thông minh:** Khi CSDL tạm thời ngắt kết nối (ví dụ khi chạy test offline), `CandidateRetriever` tự động chuyển sang đọc dữ liệu từ `data/sample_articles.csv` để không làm sập ứng dụng.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bắt buộc dùng Truy vấn Tham số (Parameterized Queries):** Tuyệt đối không dùng chuỗi f-string định dạng SQL (`f"SELECT ... WHERE id = '{id}'"`) để triệt tiêu hoàn toàn nguy cơ tấn công SQL Injection.
- **Đăng ký pgvector:** Trong `get_db_connection()`, bắt buộc gọi `pgvector.psycopg.register_vector(conn)` để driver tự động giải mã mảng số thực 768 chiều thành NumPy array.
