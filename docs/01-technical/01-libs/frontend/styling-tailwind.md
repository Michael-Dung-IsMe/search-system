# TailwindCSS: Hệ Thống Thiết Kế & Định Kiểu Utility-First

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `tailwindcss`, `@tailwindcss/turbopack`
- **Phiên bản:** `^4.0.0`
- **Vai trò trong hệ thống:** Bộ công cụ định kiểu giao diện theo triết lý utility-first, cung cấp hệ thống design tokens, màu sắc, bố cục lưới (Grid/Flexbox) và hiệu ứng chuyển động mượt mà.

## 2. Cài để làm gì?
- Định hình phong cách thiết kế hiện đại, sang trọng cho ứng dụng thời trang Lookbook Studio: nền kính mờ (`backdrop-blur`), viền thanh mảnh (`border-gray-200/50`), bo góc lớn (`rounded-2xl`).
- Xây dựng layout đáp ứng (Responsive Grid) cho danh sách sản phẩm thời trang (1 cột mobile, 2 cột tablet, 4 cột desktop).
- Tạo các hiệu ứng tương tác tức thì: hover zoom card sản phẩm (`group-hover:scale-105`), chip badge nổi bật (`bg-amber-50 text-amber-700`).

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - TailwindCSS v4 là kiến trúc thế hệ mới, tối ưu hóa biên dịch trực tiếp với Turbopack thông qua plugin `@tailwindcss/turbopack`.
  - Zero-runtime CSS: Không làm chậm quá trình render của trình duyệt so với CSS-in-JS (như Styled-components hay Emotion).
  - Không cần duy trì các file CSS riêng lẻ cồng kềnh, dễ dàng tái cấu trúc UI.
- **Phương án thay thế đã cân nhắc:**
  - *CSS Modules / Vanilla CSS*: Kiểm soát tốt nhưng tốc độ phát triển giao diện chậm và khó đồng bộ bảng mã màu giữa 11 component.
  - *Material UI / Ant Design*: Nặng nề, mang tính khuôn mẫu văn phòng, không phù hợp với thẩm mỹ thời trang cao cấp của dự án.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `web/src/app/globals.css` | Khai báo chỉ thị `@import "tailwindcss";` và biến màu sắc toàn cục | [globals.css](../../../../web/src/app/globals.css) |
| `web/src/components/ProductCard.tsx` | Styling thẻ sản phẩm, tỷ lệ khung hình ảnh thời trang (`aspect-[3/4]`), badge điểm khớp | [ProductCard.tsx](../../../../web/src/components/ProductCard.tsx) |
| `web/src/components/StateChipsBar.tsx` | Styling các chip bộ lọc có nút gỡ bỏ `[✕]` | [StateChipsBar.tsx](../../../../web/src/components/StateChipsBar.tsx) |
| `web/src/components/StickyRefineBar.tsx` | Styling thanh tìm kiếm dính ở chân trang (`fixed bottom-6 z-40`) | [StickyRefineBar.tsx](../../../../web/src/components/StickyRefineBar.tsx) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức trên toàn bộ giao diện `web/`.
- **Cấu hình:** Sử dụng cấu hình không cần file `tailwind.config.js` truyền thống nhờ cơ chế cấu hình tự động của Tailwind v4.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Tối ưu Bundle:** Turbopack tự động loại bỏ (purge) toàn bộ class CSS không được sử dụng, giữ file CSS sản phẩm cuối cùng dưới 30KB.
- **Dynamic Classes:** Không nối chuỗi động các class Tailwind (ví dụ: `text-${color}-500`) mà sử dụng class đầy đủ hoặc map từ điển để trình biên dịch quét chính xác.
