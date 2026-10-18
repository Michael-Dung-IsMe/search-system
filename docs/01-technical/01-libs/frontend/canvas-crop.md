# HTML5 Canvas API: Xử Lý Đồ Họa & Cắt Vùng Trang Phục Tương Tác

## 1. Thông tin tổng quan & Phiên bản
- **Công nghệ:** `HTML5 Canvas API` (Native Browser Standard)
- **Cơ chế triển khai:** Trực tiếp qua `CanvasRenderingContext2D` trong React components mà không cần cài thêm thư viện wrapper cồng kềnh.
- **Vai trò trong hệ thống:** Hiển thị ảnh phối đồ (outfit), vẽ overlay khung chữ nhật và đường viền contour polygon bao quanh từng món đồ thời trang (áo, quần, giày, túi) được AI phát hiện, cho phép người dùng click chọn và crop ảnh trực tiếp tại client.

## 2. Cài để làm gì?
- **Ánh xạ tọa độ chuẩn hóa sang tọa độ pixel thực:** Mô hình OWL-ViT từ Backend trả về tọa độ chuẩn hóa dạng tỷ lệ `[ymin, xmin, ymax, xmax]` trong khoảng `[0.0, 1.0]`. Canvas chuyển đổi linh hoạt tọa độ này sang kích thước hiển thị thực tế trên màn hình người dùng.
- **Vẽ Bounding Boxes & Polygons:** Tô màu viền nổi bật (Neon Blue/Amber), vẽ nhãn phân loại (như *"Top 94%"*, *"Pants 88%"*), và hiển thị hiệu ứng hover/active khi trỏ chuột vào món đồ.
- **Trích xuất ảnh cắt (Client-side Crop):** Khi người dùng chốt vùng chọn, Canvas thực hiện cắt vùng ảnh tương ứng qua `ctx.drawImage(...)` và xuất ra `Blob` (JPEG chất lượng cao) để gửi trực tiếp lên endpoint `/api/search`.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Native Browser Engine**: Hiệu năng vẽ mượt mà đạt 60fps, không phụ thuộc vào thư viện bên thứ 3 hay gặp vấn đề tương thích khi nâng cấp phiên bản React.
  - Kiểm soát tuyệt đối từng nét vẽ (Stroke style, Dashed lines, Alpha transparency).
  - Tự do scale theo tỉ lệ màn hình retina/high-DPI mà không bị vỡ hạt.
- **Phương án thay thế đã cân nhắc:**
  - *react-image-crop / cropperjs*: Chỉ hỗ trợ kéo tay 1 khung đơn lẻ, không hỗ trợ hiển thị đồng thời nhiều bounding box nhận diện tự động từ AI.
  - *SVG Overlay*: Dễ styling nhưng khi thực hiện lệnh crop trích xuất ảnh pixel thì vẫn buộc phải vẽ lên Canvas, do đó dùng trực tiếp Canvas là giải pháp tối ưu và tinh gọn nhất.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `web/src/components/ObjectSelectModal.tsx` | Quản lý Canvas, xử lý sự kiện `onMouseMove`, `onClick` để phát hiện box đang trỏ vào và render overlay | [ObjectSelectModal.tsx](../../../../web/src/components/ObjectSelectModal.tsx) |
| `web/src/components/ImageAnalysisBar.tsx` | Hiển thị thumbnail ảnh đã crop làm tham chiếu tìm kiếm trực quan | [ImageAnalysisBar.tsx](../../../../web/src/components/ImageAnalysisBar.tsx) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức (Production).
- **Tính năng nổi bật:** Hỗ trợ cả 2 chế độ:
  1. *Chế độ AI Tự Động*: Click vào bất kỳ hộp nào mà OWL-ViT phát hiện được.
  2. *Chế độ Thủ Công*: Người dùng tự kéo thả chuột để khoanh vùng tự do nếu AI bỏ sót chi tiết nhỏ.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Scale tỷ lệ màn hình (DPI scaling):** Khi render trên màn hình Retina, cần nhân kích thước canvas với `window.devicePixelRatio` để các đường viền nét chữ không bị mờ nhòe.
- **Giải phóng bộ nhớ:** Khi đóng modal hoặc đổi ảnh khác, giải phóng đối tượng `Image` và hủy URL đối tượng tạm bằng `URL.revokeObjectURL(url)`.
