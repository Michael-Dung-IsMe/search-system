# Testing: Jest & React Testing Library

## 1. Thông tin tổng quan & Phiên bản
- **Tên packages:** `jest`, `jest-environment-jsdom`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`
- **Phiên bản:**
  - `jest`: `^30.5.2`
  - `@testing-library/react`: `^16.3.3`
  - `@testing-library/jest-dom`: `^7.0.1`
  - `@testing-library/user-event`: `^14.6.8`
- **Vai trò trong hệ thống:** Bộ công cụ kiểm thử tự động toàn diện cho tầng Frontend: unit test các component, kiểm thử hành vi tương tác người dùng (user events) và contract test tầng client API.

## 2. Cài để làm gì?
- Kiểm thử hành vi render và tương tác của từng component UI độc lập (Component Unit Testing).
- Mô phỏng chuỗi tương tác phức tạp của người dùng: Gõ phím tìm kiếm, nhấn nút thu âm giọng nói, chọn file upload, click vùng bounding box, và nhấn nút `[✕]` gỡ chip.
- Giả lập (Mock) các phản hồi mạng của API (`jest.mock('@/lib/api')`) để kiểm tra trạng thái hiển thị: Lưới rỗng (*Empty state*), Đang tải (*Loading state*), Báo lỗi kết nối (*Network Error Banner*).
- Đo lường và đảm bảo tỷ lệ bao phủ mã nguồn (Code Coverage).

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - Bộ đôi **Jest + React Testing Library** là tiêu chuẩn công nghiệp cho hệ sinh thái React, kiểm thử theo góc nhìn của người dùng thực tế (*"The more your tests resemble the way your software is used, the more confidence they can give you"*).
  - Tích hợp matchers phong phú từ `@testing-library/jest-dom` (`toBeInTheDocument()`, `toHaveValue()`).
- **Phương án thay thế đã cân nhắc:**
  - *Vitest*: Rất nhanh nhưng cấu hình với Next.js App Router và Turbopack cần nhiều thiết lập bổ sung so với cấu hình Jest chuẩn hóa của Next.js.
  - *Cypress / Playwright*: Dành cho kiểm thử End-to-End thực tế trên trình duyệt thật (nặng hơn và chạy chậm hơn so với kiểm thử unit/integration với jsdom).

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn kiểm thử | Đối tượng kiểm thử chính | Đường dẫn trực tiếp |
|---|---|---|
| `web/__tests__/SearchBar.test.tsx` | Nhập text, voice recording, file input trigger | [SearchBar.test.tsx](../../../../web/__tests__/SearchBar.test.tsx) |
| `web/__tests__/ObjectSelectModal.test.tsx` | Render Canvas, click chọn bounding box, nút crop xác nhận | [ObjectSelectModal.test.tsx](../../../../web/__tests__/ObjectSelectModal.test.tsx) |
| `web/__tests__/ProductCard.test.tsx` | Hiển thị thông tin sản phẩm, giá VND, nhãn giải thích | [ProductCard.test.tsx](../../../../web/__tests__/ProductCard.test.tsx) |
| `web/__tests__/api.test.ts` | Gọi 5 endpoint REST API, xử lý lỗi `ApiError` | [api.test.ts](../../../../web/__tests__/api.test.ts) |
| `web/__tests__/page.test.tsx` | Tích hợp toàn diện luồng tìm kiếm trên trang chủ | [page.test.tsx](../../../../web/__tests__/page.test.tsx) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Toàn bộ 9 test suite nằm trong thư mục `web/__tests__/`.
- **Lệnh thực thi:**
  ```bash
  cd web
  npm test -- --watchAll=false
  ```

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Mock Canvas Context:** Trong môi trường Node/JSDOM, phương thức `HTMLCanvasElement.prototype.getContext('2d')` được mock trong `web/jest.setup.js` để tránh lỗi null context khi kiểm thử component vẽ Canvas.
- **Async Act & WaitFor:** Các hành vi cập nhật state bất đồng bộ sau khi gọi mock API cần được bao bọc trong `await waitFor(() => { ... })` để đảm bảo DOM đã cập nhật hoàn toàn trước khi kiểm tra assertion.
