# Next.js: Nền Tảng Ứng Dụng Web & App Router

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `next`
- **Phiên bản:** `16.4.0` (Turbopack tích hợp)
- **Vai trò trong hệ thống:** Framework nền tảng cho Lookbook Studio Frontend, quản lý App Router, routing, render phía client/server và tối ưu tài nguyên tĩnh.

## 2. Cài để làm gì?
- Cung cấp cấu trúc ứng dụng Single-Page Search App hiện đại thông qua mô hình **App Router (`src/app/`)**.
- Tối ưu hóa bundle và tốc độ khởi động trang nhờ bộ biên dịch **Turbopack** (`--turbo`).
- Tích hợp sẵn font hệ thống tối ưu (`next/font` Geist) và quản lý metadata trang tìm kiếm.
- Quản lý môi trường thực thi và hot-reloading phục vụ phát triển giao diện tìm kiếm thời trang tương tác.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Kiến trúc App Router phân tách tự nhiên giữa Server Components và Client Components (`'use client'`).
  - Hỗ trợ bundling cực nhanh với Turbopack (giảm thời gian khởi động dev server xuống dưới 1s).
  - Tích hợp chuẩn hóa với hệ sinh thái React 19 và TailwindCSS v4.
- **Phương án thay thế đã cân nhắc:**
  - *Vite + React SPA*: Rất nhanh nhưng thiếu cơ chế routing linh hoạt chuẩn doanh nghiệp và tối ưu font/metadata tự động.
  - *Create React App (CRA)*: Đã lỗi thời, không tương thích tốt với React 19 và Turbopack.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `web/package.json` | Khai báo dependency `next: 16.4.0` và scripts dev/build | [package.json](../../../../web/package.json) |
| `web/next.config.ts` | Cấu hình Next.js compiler và image domains | [next.config.ts](../../../../web/next.config.ts) |
| `web/src/app/layout.tsx` | Root Layout, nạp font Geist và metadata trang | [layout.tsx](../../../../web/src/app/layout.tsx) |
| `web/src/app/page.tsx` | Trang tìm kiếm tương tác chính (`'use client'`) | [page.tsx](../../../../web/src/app/page.tsx) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Đang chạy chính thức (Production-ready).
- **Cơ chế hoạt động:** Chạy ở chế độ Client-side Component (`'use client'`) trên toàn bộ trang `page.tsx` nhằm phục vụ việc tương tác Canvas và cập nhật trạng thái tìm kiếm thời gian thực.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Client vs Server Components:** Do ứng dụng tìm kiếm có tính tương tác cao (ghi âm qua Web Audio API, chọn bounding box qua Canvas, kéo thanh trượt facet lọc giá), `page.tsx` phải được đánh dấu `'use client'`.
- **Port kết nối:** Frontend Next.js mặc định lắng nghe tại cổng `3000` (`http://localhost:3000`), kết nối sang backend FastAPI tại cổng `8000`.
