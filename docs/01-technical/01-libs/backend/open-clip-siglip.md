# OpenCLIP & Marqo-fashionSigLIP: Mô Hình Embedding Thị Giác Thời Trang 768 Chiều

## 1. Thông tin tổng quan & Phiên bản
- **Tên packages:** `open_clip_torch`, `torchvision`, `pillow`
- **Phiên bản:** `open_clip_torch>=2.24.0`, `torchvision>=0.19.0`, `pillow>=10.0.0`
- **Checkpoint Model:** `hf-hub:Marqo/marqo-fashionSigLIP` (kiến trúc `ViT-B-16-SigLIP`, không gian nhúng thị giác 768 chiều).
- **Vai trò trong hệ thống:** Tầng Trích xuất Đặc trưng Thị giác (Image Embedding Engine), chuyên trách mã hóa hình ảnh sản phẩm và các vùng cắt trang phục (crop outfit) thành vector 768 chiều. (Lưu ý: Hệ thống áp dụng kiến trúc **Hybrid Embedding**; phần Text Embedding cho truy vấn văn bản/giọng nói được ủy nhiệm chính thức cho OpenAI `text-embedding-3-small`, trong khi SigLIP Text Encoder đóng vai trò là cơ chế fallback cục bộ).

## 2. Cài để làm gì?
- **Trích xuất Vector Ảnh (Image Encoding - Vai trò chính):** Nhận ảnh đầu vào (ảnh sản phẩm catalog hoặc ảnh crop món đồ từ outfit người dùng upload), resize và chuẩn hóa qua `SigLIP preprocessor`, đưa qua Vision Transformer để sinh ra vector đặc trưng thị giác 768 chiều.
- **Mã hóa Văn bản Cục bộ (Local Fallback Text Encoding):** Sẵn sàng mã hóa câu mô tả tiếng Anh khi hệ thống chạy ở chế độ ngoại tuyến không có internet hoặc không cấu hình `OPENAI_API_KEY`.
- **Độ chính xác chi tiết may mặc:** Nhận diện xuất sắc hoa văn, chất liệu vải, kiểu cổ áo, độ dài ống tay và kiểu dáng cắt may nhờ tập dữ liệu huấn luyện thời trang chuyên sâu.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Chuyên biệt cho Thời trang (Fashion-domain specific)**: Được huấn luyện trên hàng triệu cặp ảnh - mô tả thời trang thực tế (e-commerce catalog), nhận diện tốt các chi tiết cắt may (collar, sleeve, fit, material).
  - **Hàm mất mát SigLIP (Sigmoid Loss for Language Image Pre-training)**: Vượt trội hơn hàm Softmax chuẩn của CLIP gốc của OpenAI, đặc biệt ở khả năng phân biệt chi tiết nhỏ và các mẫu hiếm.
  - Kích thước vừa vặn (~1.8GB VRAM ở chế độ FP16), chạy mượt mà trên card đồ họa NVIDIA GeForce GTX 1660 Ti (6GB VRAM).
- **Kiến trúc Hybrid Embedding & Phân tách Không gian (Dual-space Separation):**
  - Trong tìm kiếm thời trang, mô tả văn bản của người dùng có thể là tiếng Việt giàu sắc thái ngữ cảnh (*"áo sơ mi cộc tay dáng rộng đi biển"*), trong khi ảnh sản phẩm đòi hỏi độ nhạy thị giác cực cao.
  - Hệ thống tách biệt 2 luồng: Truy vấn Text/Voice so sánh với `p.text_embedding` (OpenAI 768-D), còn truy vấn Ảnh Crop so sánh với `p.image_embedding` (SigLIP 768-D). Hai không gian hoàn toàn độc lập, tránh sự suy giảm chất lượng khi ép một mô hình phải đảm nhiệm tốt cả hai ngôn ngữ và thị giác.
- **Phương án thay thế đã cân nhắc:**
  - *OpenAI CLIP (ViT-B/32)*: Huấn luyện trên dữ liệu web chung, thường nhận diện sai chất liệu vải và phom dáng thời trang chuyên dụng.
  - *Fashion-CLIP (PatrickJohnCyprus)*: Kích thước 512 chiều, độ chính xác nhận diện mẫu trang phục phức tạp thấp hơn SigLIP 768 chiều.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/core/embedder.py` | Class `MultimodalEmbedder` (Singleton), hàm `encode_image()`, `encode_text()` | [embedder.py](../../../../backend/core/embedder.py) |
| `backend/routes/search_routes.py` | Mã hóa ảnh crop upload hoặc câu query thành vector tìm kiếm | [search_routes.py](../../../../backend/routes/search_routes.py#L156-L208) |
| `scripts/index_products.py` | Đọc 5.000 ảnh sản phẩm H&M và tính vector lưu vào DB | [index_products.py](../../../../scripts/index_products.py#L45-L95) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức (Production).
- **Cơ chế Singleton & Caching:** Model được khởi tạo duy nhất 1 lần khi server start để tránh tốn thời gian nạp lại trọng số vào GPU.
- **Hỗ trợ chế độ Mock (`use_mock=True`):** Khi chạy unit test tự động, class trả về vector giả lập 768 chiều ngẫu nhiên chuẩn hóa để test chạy tức thì mà không cần nạp trọng số nặng.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Quản lý VRAM GPU:** Chiếm xấp xỉ **1.8GB VRAM**.
- **Inference Mode & FP16:** Luôn bọc trong khối `with torch.no_grad():` và ép kiểu `model.eval()` để PyTorch không lưu đồ thị tính đạo hàm (Gradient Graph), tiết kiệm hơn 50% bộ nhớ.
- **L2 Normalization:** Luôn thực hiện `vector = vector / np.linalg.norm(vector)` trước khi trả về.
