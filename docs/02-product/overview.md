# Tổng quan sản phẩm

Hệ thống giúp người dùng tìm sản phẩm thời trang bằng text, voice, image hoặc image + text. Mỗi thao tác tìm là một request độc lập và phải chứa đầy đủ điều kiện cần áp dụng.

## Giá trị chính

- Tìm bằng tiếng Việt tự nhiên thay vì nhập từng trường thủ công.
- Tải outfit và chọn đúng vùng áo, quần, váy hoặc giày.
- Dùng ảnh làm mẫu hình dáng, đồng thời dùng text để đổi màu, giá hoặc loại cụ thể.
- Tìm sản phẩm tương tự từ một product card.
- Hiển thị exact matches và controlled-relaxation suggestions riêng biệt.
- Chỉ hiển thị `% khớp ảnh` cho truy vấn thực sự dùng image embedding.

## Thành phần giao diện

| Component | Vai trò |
|---|---|
| `SearchBar` | Text, upload ảnh, ghi âm 20 giây |
| `ImageAnalysisBar` | Hiện trạng thái và vùng ảnh được chọn |
| `ObjectSelectModal` | Chọn bounding box trong outfit |
| `RecommendedPills` | Shortcut danh mục |
| `FacetSidebar` | Chọn category, màu và giá; gửi toàn bộ facet trong một request mới |
| `ProductGrid` | Hiển thị exact/similar/conversation response |
| `ProductCard` | Thông tin sản phẩm và tìm tương tự |

## Phạm vi hiện tại

Backend không duy trì session tìm kiếm, không có thanh tinh chỉnh nhiều lượt và không có chip constraint phía server. Nếu người dùng muốn thay đổi yêu cầu, frontend gửi một query đầy đủ mới.
