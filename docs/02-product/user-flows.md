# Luồng người dùng

## 1. Tìm bằng text

1. Người dùng nhập yêu cầu đầy đủ.
2. Frontend gọi `POST /api/search`.
3. Backend trích intent, tạo `SearchState` của request, retrieve và rerank.
4. Frontend hiển thị exact hoặc similar results.

Ví dụ: `Tìm quần short màu trắng dưới 1 triệu`.

## 2. Tìm bằng voice

1. Người dùng ghi âm tối đa 20 giây.
2. Frontend gọi `/api/transcribe`.
3. Transcript được gửi sang `/api/search` với `query_type=voice`.
4. Phần còn lại giống text search.

## 3. Tìm bằng ảnh

1. Người dùng tải ảnh.
2. Frontend đồng thời tìm bằng toàn ảnh và gọi `/api/detect`.
3. Nếu có nhiều vật thể, người dùng chọn box.
4. Frontend gửi lại ảnh cùng `crop_box` trong một request mới.
5. Backend tạo FashionSigLIP embedding và tìm trên `image_embedding`.

## 4. Tìm bằng ảnh + text

1. Người dùng tải ảnh và chọn vật thể nếu cần.
2. Người dùng nhập toàn bộ điều kiện muốn thay đổi, ví dụ `quần short màu hồng dưới 1 triệu`.
3. Frontend gửi image, crop box và text trong cùng `/api/search` request.
4. Ảnh cung cấp độ tương đồng hình dáng; text cung cấp category/màu/giá.

## 5. Dùng facet

Facet là state cục bộ của frontend. Mỗi lần thay category, màu hoặc giá, `page.tsx` ghép toàn bộ facet hiện tại thành query mới. Backend không nhớ lần chọn trước.

## 6. Tìm sản phẩm tương tự

1. Người dùng bấm `Tìm tương tự` trên product card.
2. Frontend gửi `reference_article_id`.
3. Backend lấy `image_embedding` của sản phẩm làm query vector.
4. Kết quả được tìm trong image vector space.
