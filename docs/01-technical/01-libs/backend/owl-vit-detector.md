# OWL-ViT: Mô Hình Phát Hiện Đối Tượng Thời Trang Mở Không Cần Huấn Luyện

## 1. Thông tin tổng quan & Phiên bản
- **Tên framework:** Hugging Face `transformers`, `torch`, `pillow`
- **Checkpoint Model:** `google/owlvit-base-patch32` (hoặc `google/owlv2-base-patch16-ensemble`)
- **Vai trò trong hệ thống:** Tầng Thị giác Máy tính (Computer Vision / Object Detection Engine), phát hiện và khoanh vùng chính xác các món đồ thời trang (quần áo, giày dép, túi xách) xuất hiện trong một bức ảnh phối đồ (outfit) theo từ khóa tự do (Zero-shot Open-vocabulary Object Detection).

## 2. Cài để làm gì?
- Tiếp nhận ảnh phối đồ toàn thân (*full outfit look*) từ người dùng tải lên.
- Quét ảnh với tập nhãn truy vấn mở (*text prompts*): `["shirt", "jacket", "t-shirt", "pants", "jeans", "skirt", "dress", "shoes", "sneakers", "bag", "handbag", "hat"]`.
- Trả về danh sách các bounding boxes chuẩn hóa `[ymin, xmin, ymax, xmax]` kèm nhãn thời trang chuẩn và điểm số tự tin (*Confidence Score*).
- Tính toán contour polygon (đa giác 16 điểm) bao quanh món đồ phục vụ hiển thị viền tương tác trên giao diện Web.
- Cung cấp hàm tiện ích cắt ảnh (`crop_bounding_box`) với cơ chế kẹp biên an toàn (*boundary clamp*) để chuẩn bị ảnh đưa sang model Embedding.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Open-Vocabulary (Từ vựng mở)**: Không bị giới hạn trong 80 nhãn cố định của tập dữ liệu COCO thông thường. Có thể phát hiện bất kỳ khái niệm thời trang nào thông qua văn bản mô tả.
  - Tách bạch xuất sắc giữa các lớp trang phục chồng lấn (ví dụ: áo khoác ngoài blazer và áo thun mặc bên trong).
  - VRAM footprint gọn gàng (~1.5GB VRAM), hoàn toàn có thể chạy đồng thời với SigLIP trên GPU 6GB GTX 1660 Ti.
- **Phương án thay thế đã cân nhắc:**
  - *YOLOv8 / YOLOv10*: Tốc độ nhanh hơn nhưng phải huấn luyện lại (fine-tune) trên tập dữ liệu thời trang riêng, kém linh hoạt khi muốn thêm các danh mục phụ kiện mới.
  - *Grounding DINO*: Rất mạnh nhưng ngốn tới 4.5GB VRAM, sẽ làm tràn bộ nhớ GPU 6GB khi chạy cùng lúc với PostgreSQL và SigLIP.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/core/detector.py` | Class `ObjectDetector` (Singleton), các hàm `detect()`, `crop_bounding_box()`, `extract_contour_polygon()` | [detector.py](../../../../backend/core/detector.py) |
| `backend/routes/search_routes.py` | Endpoint `POST /api/detect` và xử lý cắt ảnh crop_box trong `POST /api/search` | [search_routes.py](../../../../backend/routes/search_routes.py#L52-L84) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức (Production).
- **Bộ đệm MD5 Hash:** Hàm `compute_image_hash()` sinh chuỗi băm MD5 của ảnh upload; nếu cùng một bức ảnh được gửi lại, hệ thống có thể trả kết quả ngay lập tức từ bộ nhớ đệm.
- **Mock Mode (`use_mock=True`):** Tự động sinh ra 3 bounding boxes mẫu (Top, Pants, Shoes) kèm polygon chuẩn hóa để kiểm thử giao diện và API trong vài mili-giây.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Ngưỡng lọc Confidence Threshold:** Mặc định thiết lập ở mức `0.15` để không bỏ sót các phụ kiện nhỏ (túi, nón, kính râm).
- **Non-Maximum Suppression (NMS):** Áp dụng thuật toán NMS với ngưỡng IoU `0.5` để loại bỏ các hộp nhận diện trùng lặp trên cùng một món đồ.
- **Tối ưu VRAM:** Kích hoạt chế độ suy luận bán chính xác `torch.float16` trên CUDA.
