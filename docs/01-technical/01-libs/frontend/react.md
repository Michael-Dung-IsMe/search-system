# React & React-DOM: Thư Viện Giao Diện & Quản Lý Trạng Thái

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `react`, `react-dom`
- **Phiên bản:** `19.3.0`
- **Vai trò trong hệ thống:** Lõi thư viện UI xây dựng các thành phần giao diện, quản lý chu trình render, DOM references và phản hồi tương tác người dùng.

## 2. Cài để làm gì?
- Quản lý trạng thái tìm kiếm cục bộ và phản ứng tức thì (`useState`, `useReducer`).
- Đồng bộ hóa hiệu ứng và vòng đời thành phần (`useEffect`, `useCallback`).
- Tương tác trực tiếp với DOM phần tử HTML5 Canvas phục vụ vẽ bounding box và crop ảnh (`useRef`).
- Render các module UI chính: SearchBar, ObjectSelectModal, ImageAnalysisBar, FacetSidebar, ProductGrid và ProductCard.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Phiên bản React 19 mang lại hiệu năng compiler vượt trội, cơ chế tối ưu hóa render tự động giảm thiểu re-render không cần thiết.
  - Hệ sinh thái rộng lớn, tương thích hoàn hảo với Next.js 16 và các thư viện icon/styling hiện đại.
- **Phương án thay thế đã cân nhắc:**
  - *Vue 3 / Svelte*: Rất nhẹ và nhanh nhưng hệ sinh thái thư viện canvas và component dựng sẵn cho AI Lookbook không phong phú bằng React.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `web/src/app/page.tsx` | Quản lý toàn bộ State chính: `sessionState`, `searchResults`, `selectedBox` | [page.tsx](../../../../web/src/app/page.tsx) |
| `web/src/components/ObjectSelectModal.tsx` | Sử dụng `useRef<HTMLCanvasElement>` để vẽ bounding box tương tác | [ObjectSelectModal.tsx](../../../../web/src/components/ObjectSelectModal.tsx) |
| `web/src/components/SearchBar.tsx` | Quản lý state ghi âm giọng nói và trạng thái uploading | [SearchBar.tsx](../../../../web/src/components/SearchBar.tsx) |
| `web/src/components/FacetSidebar.tsx` | State lọc cứng (khoảng giá, danh mục, màu sắc, giới tính) | [FacetSidebar.tsx](../../../../web/src/components/FacetSidebar.tsx) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức trên 100% các components trong `web/src/components/`.
- **Cơ chế hoạt động:** Single-page reactive state, giao tiếp với API qua asynchronous hooks và Event Handlers.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Tránh re-render khi gõ phím:** State text query trong `SearchBar` được cô lập cục bộ, chỉ phát tín hiệu tìm kiếm khi submit hoặc kết thúc lượt ghi âm.
- **Tương thích React 19:** Một số thư viện React cũ có thể cảnh báo `peerDependencies` với React 19; dự án đã lựa chọn các thư viện tương thích tuyệt đối (`lucide-react`, Tailwind v4).
