# Data Processing: Pandas & NumPy Trong Xử Lý Dữ Liệu Thời Trang

## 1. Thông tin tổng quan & Phiên bản
- **Tên packages:** `pandas`, `numpy`, `scikit-learn`
- **Phiên bản:** `pandas>=2.0.0`, `numpy>=1.26.0`
- **Vai trò trong hệ thống:** Tầng Xử lý Dữ liệu Ngoại tuyến & Tính toán Khoa học (ETL & Numerical Engine), phục vụ chọn mẫu đại diện (Stratified Sampling), tiền xử lý bảng dữ liệu thời trang H&M, chuẩn hóa vector và tính toán ma trận tương đồng.

## 2. Cài để làm gì?
- **Chọn mẫu phân tầng (Stratified Sampling) 5.000 sản phẩm:**
  - Đọc tập dữ liệu khổng lồ H&M từ Kaggle (`articles.csv` gồm hơn 105.000 dòng).
  - Phân tầng chính xác theo tỷ lệ giới tính (60% Nữ / Ladieswear, 40% Nam / Menswear).
  - Phân tầng cân đối theo 6 nhóm danh mục trang phục chính: Garment Upper body (40%), Garment Lower body (25%), Dresses (15%), Shoes (10%), Bags (5%), Accessories (5%).
- **Làm giàu và chuẩn hóa dữ liệu:**
  - Quy đổi giá niêm yết sang tiền Việt Nam Đồng (VND) thực tế trong khoảng 199.000đ đến 2.490.000đ theo bước giá 50.000đ/100.000đ.
  - Ánh xạ mã màu thời trang H&M về 20 màu sắc cơ bản và bảng từ đồng nghĩa đa ngữ.
- **Tính toán mảng số học (Vector Math):**
  - Thực hiện chuẩn hóa L2 norm cho các vector 768 chiều (`norm = np.linalg.norm(vec); vec = vec / norm`).
  - Hỗ trợ tính toán khoảng cách vector và sắp xếp thứ hạng khi chạy chế độ offline không dùng PostgreSQL (`retrieve_from_csv_partitioned`).

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Pandas 2.0+**: Hỗ trợ backend Apache Arrow, xử lý lọc và gom nhóm dataframe 105.000 dòng chỉ mất chưa đầy 0.5 giây.
  - **NumPy 1.26+**: Thư viện tính toán mảng C-extension nhanh nhất cho Python, tương thích tuyệt đối với PyTorch và pgvector.
- **Phương án thay thế đã cân nhắc:**
  - *Polars*: Rất nhanh nhưng hệ sinh thái tích hợp với các pipeline PyTorch và scikit-learn hiện tại của dự án chưa phổ biến bằng Pandas/NumPy.
  - *Python thuần (list/dict)*: Quá chậm khi tính toán vector 768 chiều trên 5.000 phần tử (chậm hơn 40 lần so với NumPy vectorization).

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `scripts/sample_dataset.py` | Hàm `stratified_sample()` đọc `articles.csv` và tạo `data/sample_articles.csv` | [sample_dataset.py](../../../../scripts/sample_dataset.py) |
| `scripts/index_products.py` | Lặp dataframe, tính vector và insert vào PostgreSQL | [index_products.py](../../../../scripts/index_products.py) |
| `backend/core/retriever.py` | Hàm `retrieve_from_csv_partitioned()` sử dụng Pandas và NumPy khi DB offline | [retriever.py](../../../../backend/core/retriever.py#L320-L370) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức. File `data/sample_articles.csv` (5.000 mẫu đại diện) đã được tạo và lưu trữ an toàn trong kho dữ liệu dự án.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bảo toàn dữ liệu thiếu (Deficit Fill):** Khi một nhóm danh mục con không đủ số lượng theo tỷ lệ, thuật toán trong `sample_dataset.py` tự động bù đắp (deficit redistribution) từ các danh mục cùng nhóm để luôn đảm bảo chính xác 5.000 mẫu hợp lệ.
- **Kiểu dữ liệu float32:** Luôn ép kiểu vector nhúng về `np.float32` để đảm bảo tương thích hoàn hảo với định dạng `vector(768)` của PostgreSQL pgvector.
