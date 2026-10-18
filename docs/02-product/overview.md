# Tổng Quan Sản Phẩm & Ma Trận Đối Soát Giao Diện UI

Tài liệu này thuyết minh bài toán nghiệp vụ của đề tài **Hệ thống Tìm kiếm Thời trang Đa phương thức Tương tác (Interactive Multimodal Shopping Search Engine)** thuộc học phần Phân tích & Thiết kế Hệ thống Thông tin (PTTK-HTTT), đồng thời đối soát chi tiết **11 thành phần giao diện (UI Components)** với các endpoints Backend thực tế.

---

## 1. Bài Toán Nghiệp Vụ & Giá Trị Giải Pháp

### 1.1. Vấn đề của tìm kiếm thương mại điện tử truyền thống
- **Nghẽn từ khóa (Keyword Barrier)**: Người dùng nhìn thấy một bộ trang phục đẹp nhưng không biết gọi tên chính xác chất liệu, kiểu dáng hay form cắt thời trang (ví dụ: không biết gọi là *"áo blazer dáng suông oversize"* hay *"blazer chiết eo"*).
- **Thiếu tính tương tác đa lượt (Single-shot Failure)**: Khi kết quả trả về không như ý, người dùng buộc phải xóa toàn bộ ô tìm kiếm và gõ lại từ đầu, làm đứt gãy luồng cảm hứng mua sắm.
- **Rời rạc giữa thị giác và văn bản**: Người dùng không thể vừa dùng ảnh của một bộ phối đồ vừa bổ sung các ràng buộc bằng lời nói hoặc chữ (*"tìm cái áo trong ảnh này nhưng giá dưới 500k và không phải vải nỉ"*).

### 1.2. Giải pháp: Lookbook Studio Tìm Kiếm Tương Tác
- Cho phép người dùng tải lên ảnh phối đồ bất kỳ $\to$ AI tự động bóc tách từng món đồ riêng lẻ.
- Người dùng chỉ cần click chọn món đồ muốn mua và tiếp tục nói hoặc gõ các yêu cầu tinh chỉnh.
- Hệ thống duy trì ngữ cảnh phiên làm việc xuyên suốt nhiều lượt (*Conversational Refinement*), hiển thị các thẻ tiêu chí trực quan và cho phép gỡ bỏ bộ lọc tức thì.

---

## 2. Ma Trận Đối Soát 11 Thành Phần UI Với API Backend

Toàn bộ 11 thành phần giao diện trong thư mục `web/src/components/` được đối chiếu trực tiếp với mã nguồn và endpoints backend:

| STT | Tên Component | File mã nguồn | Vai trò nghiệp vụ | Endpoint Backend kết nối | Trạng thái thực tế |
|:---:|---|---|---|---|:---:|
| 1 | `SearchBar` | `web/src/components/SearchBar.tsx` | Nhập văn bản tự do, ghi âm giọng nói qua Mic, kích hoạt chọn ảnh upload | `POST /api/search`<br/>`POST /api/transcribe` | **Đủ** |
| 2 | `ObjectSelectModal` | `web/src/components/ObjectSelectModal.tsx` | Modal tương tác Canvas hiển thị các bounding boxes và contour polygons bao quanh trang phục | `POST /api/detect`<br/>`POST /api/search` | **Đủ** |
| 3 | `StateChipsBar` | `web/src/components/StateChipsBar.tsx` | Hiển thị các tiêu chí lọc đang có hiệu lực (giá, màu sắc, danh mục), nút `[✕]` gỡ chip | `DELETE /api/search/{sid}/constraint` | **Đủ** |
| 4 | `ProductGrid` | `web/src/components/ProductGrid.tsx` | Bố cục lưới sản phẩm phân vùng (Khớp chính xác vs Gợi ý tương tự), xử lý trạng thái rỗng | `POST /api/search` | **Đủ** |
| 5 | `ProductCard` | `web/src/components/ProductCard.tsx` | Thẻ sản phẩm thời trang: ảnh tỷ lệ 3:4, tên, giá VND, nhãn % tương đồng và Explainable Badges | `GET /api/products/{id}` | **Đủ** |
| 6 | `FacetSidebar` | `web/src/components/FacetSidebar.tsx` | Bảng điều khiển bộ lọc cứng (Khoảng giá trượt Slider, Bộ chọn màu, Danh mục, Giới tính) | `POST /api/search` | **Đủ** |
| 7 | `StickyRefineBar` | `web/src/components/StickyRefineBar.tsx` | Thanh tinh chỉnh hội thoại dính ở đáy màn hình khi cuộn trang, hỗ trợ nhập liệu nhanh | `POST /api/search`<br/>`POST /api/transcribe` | **Đủ** |
| 8 | `ConversationalFeed`| `web/src/components/ConversationalFeed.tsx` | Dòng thời gian hiển thị lịch sử các câu lệnh và phản hồi của trợ lý AI qua từng lượt | Client-side Session Log | **Đủ** |
| 9 | `ImageAnalysisBar` | `web/src/components/ImageAnalysisBar.tsx` | Thanh hiển thị preview vùng ảnh đã crop và nút quét lại vùng khác | `POST /api/detect` | **Đủ** |
| 10 | `RecommendedPills`| `web/src/components/RecommendedPills.tsx` | Các thẻ gợi ý xu hướng thời trang tìm kiếm nhanh (Áo blazer, Đầm satin...) | `POST /api/search` | **Đủ** |
| 11 | `Header` | `web/src/components/Header.tsx` | Tiêu đề ứng dụng, chuyển đổi theme, chỉ báo trạng thái kết nối máy chủ | `GET /health` | **Đủ** |

---

## 3. Quản Lý Các Trạng Thái Biên (Edge Cases)

Hệ thống được thiết kế xử lý trơn tru mọi tình huống biên:
1. **Không tìm thấy sản phẩm khớp chính xác**:
   - Khi các Hard Constraints quá ngặt nghèo (ví dụ: *"giày boot da bò dưới 100k"*), hệ thống không hiển thị màn hình trắng rỗng.
   - Thay vào đó, hệ thống hiển thị thông báo thân thiện: *"Không tìm thấy sản phẩm khớp chính xác với tiêu chí của bạn. Dưới đây là các sản phẩm tương tự"* và nới lỏng tiêu chí lọc để hiển thị danh sách sản phẩm tương đồng về kiểu dáng.
2. **File tải lên không hợp lệ hoặc quá lớn**:
   - Client tự động kiểm tra định dạng file (chỉ chấp nhận JPEG, PNG, WebP) và dung lượng (<10MB) trước khi gửi.
3. **Mất kết nối máy chủ / Ngoại tuyến**:
   - Header hiển thị chấm đỏ *"Offline Mode"*.
   - Backend tự động fallback sang tìm kiếm trên tập file dự phòng `data/sample_articles.csv` để đảm bảo hệ thống không bị crash.
