# Lucide React: Hệ Thống Biểu Tượng Giao Diện

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `lucide-react`
- **Phiên bản:** `^1.56.0`
- **Vai trò trong hệ thống:** Bộ icon vector SVG nhẹ, sắc nét và có tính tùy biến cao, cung cấp các chỉ báo trực quan cho mọi hành vi tương tác trên giao diện.

## 2. Cài để làm gì?
- Biểu thị các công cụ nhập liệu đa phương thức: Icon kính lúp (`Search`), microphone ghi âm (`Mic`, `MicOff`), camera upload ảnh (`Camera`, `Upload`).
- Biểu thị trạng thái tương tác bộ lọc: Icon đóng (`X`), phễu lọc (`Filter`), tia lửa gợi ý xu hướng (`Sparkles`, `Flame`).
- Biểu thị thông tin sản phẩm và chỉ số AI: Icon trái tim yêu thích (`Heart`), giỏ hàng (`ShoppingBag`), con mắt xem chi tiết (`Eye`), huy hiệu giải thích độ khớp (`CheckCircle`, `AlertCircle`).

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Hỗ trợ **Tree-shaking 100%**: Chỉ bundle những icon thực sự được import, kích thước chỉ vài KB.
  - Thiết kế đồng nhất theo phong cách Stroke viền mỏng (2px), thanh lịch, rất phù hợp với giao diện Lookbook thời trang.
  - Tùy biến kích thước, màu sắc và độ dày viền dễ dàng qua thuộc tính `size`, `strokeWidth`, `className`.
- **Phương án thay thế đã cân nhắc:**
  - *React Icons*: Gom quá nhiều bộ thư viện lại làm bundle nặng, thiếu tính nhất quán về visual style giữa các icon.
  - *FontAwesome*: Cồng kềnh, cần nạp web font hoặc SVG kit lớn.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Icon sử dụng | Đường dẫn trực tiếp |
|---|---|---|
| `web/src/components/SearchBar.tsx` | `Search`, `Mic`, `MicOff`, `Camera`, `Loader2` | [SearchBar.tsx](../../../../web/src/components/SearchBar.tsx) |
| `web/src/components/ObjectSelectModal.tsx` | `X`, `Crop`, `Check`, `RotateCcw`, `Scan` | [ObjectSelectModal.tsx](../../../../web/src/components/ObjectSelectModal.tsx) |
| `web/src/components/ProductCard.tsx` | `Sparkles`, `Tag`, `ChevronRight` | [ProductCard.tsx](../../../../web/src/components/ProductCard.tsx) |
| `web/src/components/StateChipsBar.tsx` | `X`, `SlidersHorizontal` | [StateChipsBar.tsx](../../../../web/src/components/StateChipsBar.tsx) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức trên 100% các components cần hiển thị biểu tượng trực quan.

## 6. Lưu ý kỹ thuật & Hiệu năng
- Luôn sử dụng cú pháp Named Import:
  ```tsx
  import { Search, Mic, Camera } from 'lucide-react';
  ```
  Tuyệt đối không dùng `import * as Icons from 'lucide-react'` để đảm bảo Turbopack có thể loại bỏ toàn bộ các icon không dùng khỏi bundle cuối cùng.
