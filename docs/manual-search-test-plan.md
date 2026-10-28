# Kịch bản kiểm thử thủ công module Search

## 1. Mục tiêu

Tài liệu này dùng để đánh giá riêng từng tầng của hệ thống tìm kiếm:

1. Hiểu ý định và chuẩn hóa câu tiếng Việt.
2. Áp dụng bộ lọc category, gender, color, price và điều kiện loại trừ.
3. Duy trì trạng thái qua nhiều lượt hội thoại.
4. Nhận diện trang phục bằng OWL-ViT.
5. Tìm ảnh tương tự bằng FashionSigLIP.
6. Truy vấn pgvector và hiển thị ảnh sản phẩm.
7. Xử lý lỗi, hiệu năng và tính ổn định.

## 2. Điều kiện trước khi test

- PostgreSQL Docker ở trạng thái `healthy`.
- Backend chạy tại `http://127.0.0.1:8000`.
- Frontend chạy tại `http://localhost:3000`.
- Endpoint `http://127.0.0.1:8000/health` trả về `status: ok`.
- Database có 1.000 sản phẩm, 1.000 `image_embedding` và 1.000 `text_embedding`.
- Ảnh chuẩn dùng để test: `data/images/0220094020.jpg`.
- Đóng tab trình duyệt cũ hoặc tải lại trang trước mỗi nhóm test độc lập.

Ghi lại cho mỗi case:

- Kết quả thực tế.
- Thời gian phản hồi.
- Số sản phẩm trả về.
- Các chip điều kiện xuất hiện.
- Sản phẩm đầu tiên.
- Ảnh chụp màn hình hoặc log backend nếu lỗi.

## 3. Kịch bản tìm kiếm văn bản

### TC-TXT-01: Tìm theo loại sản phẩm

**Thao tác:** nhập `áo thun` và bấm tìm kiếm.

**Kết quả mong đợi:**

- Không xuất hiện lỗi giao diện hoặc HTTP 500.
- Trạng thái tìm kiếm nhận diện category là `T-shirt`.
- Kết quả chủ yếu thuộc loại `T-shirt`.
- Có chip thể hiện loại sản phẩm.

**Dấu hiệu lỗi:** category sai là lỗi Intent/Normalizer; category đúng nhưng sản phẩm sai là lỗi Retriever hoặc dữ liệu category.

### TC-TXT-02: Kết hợp loại và màu

**Thao tác:** nhập `váy màu đen`.

**Kết quả mong đợi:**

- Category là `Dress`.
- Color là `Black`.
- Kết quả chính xác phải là váy đen; nếu không đủ kết quả, hệ thống ghi rõ đang hiển thị sản phẩm tương tự.
- Ảnh của từng sản phẩm tải thành công.

### TC-TXT-03: Kết hợp giới tính và giá

**Thao tác:** nhập `quần tây nam dưới 1 triệu`.

**Kết quả mong đợi:**

- Category là `Trousers`.
- Gender là `Menswear`.
- `max_price` là `1.000.000`.
- Không sản phẩm nào trong danh sách chính có giá lớn hơn 1.000.000 đồng.
- Không sản phẩm nào có gender khác `Menswear`.

### TC-TXT-04: Chuẩn hóa màu phức hợp

**Thao tác:** nhập `áo thun xanh navy`.

**Kết quả mong đợi:**

- Màu được chuẩn hóa thành `Dark Blue`, không phải `Blue` chung chung.
- Kết quả ưu tiên áo thun màu xanh đậm.

### TC-TXT-05: Chuẩn hóa lỗi phát âm/phương ngữ

**Thao tác:** nhập `dày da nam dưới 1 chiệu`.

**Kết quả mong đợi:**

- `dày` được hiểu là `giày`.
- `chiệu` được hiểu là `triệu`.
- Gender là `Menswear`.
- Giá tối đa là 1.000.000 đồng.
- Không được crash dù không có đủ sản phẩm phù hợp.

### TC-TXT-06: Điều kiện loại trừ

**Thao tác:** nhập `giày sneaker trắng dưới 1 triệu, không phải da, không màu đen`.

**Kết quả mong đợi:**

- Category là `Sneakers`, color là `White`.
- Có chip loại trừ `leather` và `Black`.
- Không kết quả chính xác nào vi phạm giá tối đa.
- Không kết quả chính xác nào có màu đen.

### TC-TXT-07: Truy vấn không có kết quả

**Thao tác:** nhập `giày nữ dưới 100 nghìn`.

**Kết quả mong đợi:**

- Không xuất hiện HTTP 500 hoặc trang trắng.
- Hệ thống hiển thị thông báo không có kết quả hoặc khu vực gợi ý tương tự.
- Không được âm thầm bỏ điều kiện giá rồi coi sản phẩm đắt hơn là kết quả chính xác.

### TC-TXT-08: Truy vấn không được hỗ trợ bởi dataset

**Thao tác:** nhập `đồng hồ đeo tay`.

**Kết quả mong đợi:**

- Không crash.
- Hệ thống không gán sai thành áo, quần, váy hoặc giày.
- Nếu trả về semantic recommendation, giao diện phải phân biệt đây là kết quả tương tự.

Lưu ý: bộ 1.000 sản phẩm hiện tại không có nhóm túi/balo, nên không dùng `balo` làm tiêu chí bắt buộc phải có kết quả.

## 4. Kịch bản hội thoại nhiều lượt

### TC-CONV-01: Tích lũy điều kiện

Chạy liên tiếp trong cùng một tab và cùng phiên:

1. `áo thun nam`
2. `màu trắng`
3. `dưới 1 triệu`
4. `không phải da`

**Kết quả mong đợi:**

- `turn_index` tăng sau mỗi lượt.
- Sau lượt 2 vẫn giữ `T-shirt` và `Menswear`.
- Sau lượt 3 vẫn giữ loại, giới tính, màu và thêm giá tối đa.
- Sau lượt 4 có thêm `leather` trong danh sách loại trừ.
- Chip trên giao diện phản ánh đầy đủ trạng thái hiện tại.

### TC-CONV-02: Xóa chip điều kiện

**Điều kiện:** thực hiện xong TC-CONV-01.

**Thao tác:** bấm dấu `X` trên chip `Không chất liệu: leather`.

**Kết quả mong đợi:**

- Chip biến mất.
- Điều kiện `exclude_materials` không còn `leather`.
- Hệ thống tự truy vấn lại kết quả.
- Các điều kiện khác vẫn được giữ nguyên.

### TC-CONV-03: Thay đổi điều kiện đang có

Chạy liên tiếp:

1. `váy màu đen`
2. `đổi sang màu trắng`

**Kết quả mong đợi:**

- Category `Dress` vẫn được giữ.
- Color cuối cùng là `White`.
- Không tồn tại đồng thời hai chip màu mâu thuẫn.

### TC-CONV-04: Tham chiếu theo thứ tự

Chạy liên tiếp:

1. `giày sneaker`
2. Quan sát và ghi lại sản phẩm thứ nhất.
3. Nhập `giống số 1 nhưng dưới 1 triệu`.

**Kết quả mong đợi:**

- `reference_article_id` bằng mã sản phẩm đứng thứ nhất ở lượt trước.
- Có chip tham chiếu sản phẩm.
- Điều kiện giá tối đa được áp dụng.
- Nếu lượt trước không có kết quả, hệ thống phải xử lý an toàn và không crash.

### TC-CONV-05: Cô lập session

**Thao tác:**

1. Tab A tìm `váy nữ màu đen`.
2. Mở tab B mới và tìm `quần nam`.

**Kết quả mong đợi:** điều kiện của tab A không xuất hiện trong tab B.

## 5. Kịch bản tìm kiếm bằng ảnh

### TC-IMG-01: Nhận diện đối tượng

**Thao tác:** upload `data/images/0220094020.jpg`.

**Kết quả mong đợi:**

- API `/api/detect` trả HTTP 200.
- Có ít nhất một bounding box hợp lệ.
- Với checkpoint hiện tại, ảnh chuẩn đã từng được nhận diện là `Skirt` với score khoảng `0.577`; score có thể dao động nhẹ.
- Bounding box nằm đúng trên sản phẩm, không nằm ngoài ảnh.

**Dấu hiệu lỗi:** không có box hoặc box sai nghiêm trọng là vấn đề OWL-ViT, threshold hoặc tiền xử lý ảnh.

### TC-IMG-02: Tìm lại chính ảnh catalog

**Thao tác:** chọn vùng sản phẩm trong ảnh chuẩn rồi thực hiện tìm kiếm.

**Kết quả mong đợi:**

- Truy vấn được đánh dấu là loại `image`.
- Có kết quả trả về.
- Sản phẩm `0220094020` hoặc sản phẩm rất giống phải nằm gần đầu danh sách.
- Điểm tương đồng không bị âm hoặc lớn hơn 1.

**Dấu hiệu lỗi:** ảnh catalog không xuất hiện gần đầu thường cho thấy vector query và vector database khác model, khác preprocessing hoặc sai ánh xạ article ID.

### TC-IMG-03: Ảnh outfit có nhiều món

**Thao tác:** upload ảnh người có ít nhất áo và quần hoặc váy và giày.

**Kết quả mong đợi:**

- OWL-ViT trả nhiều vùng độc lập nếu các món nhìn rõ.
- Chọn vùng nào thì kết quả phải tương ứng với vùng đó.
- Không dùng toàn bộ outfit khi người dùng đã chọn một crop cụ thể.

### TC-IMG-04: File không hợp lệ

**Thao tác:** thử upload file `.txt` hoặc một file ảnh hỏng.

**Kết quả mong đợi:**

- File sai định dạng trả lỗi 400.
- Giao diện hiển thị thông báo dễ hiểu.
- Backend không dừng và các truy vấn sau vẫn hoạt động.

### TC-IMG-05: Cache nhận diện

**Thao tác:** upload cùng một ảnh hai lần liên tiếp và ghi thời gian.

**Kết quả mong đợi:** lần thứ hai nhanh hơn đáng kể do cache theo MD5 trong bộ nhớ. Nếu lần hai vẫn chậm như lần đầu, kiểm tra singleton và cache detector.

## 6. Kịch bản hiển thị và API sản phẩm

### TC-UI-01: Hiển thị ảnh sản phẩm

**Thao tác:** mở kết quả bất kỳ và quan sát toàn bộ ảnh trong danh sách.

**Kết quả mong đợi:**

- Không có ảnh vỡ hoặc HTTP 404.
- URL có dạng `http://localhost:8000/images/<article_id>.jpg`.
- Ảnh đúng với mã và tên sản phẩm.

### TC-UI-02: Chi tiết sản phẩm

**Thao tác:** mở một sản phẩm từ kết quả.

**Kết quả mong đợi:** mã sản phẩm, tên, giá, gender, category, mô tả và ảnh khớp với card đã chọn.

### TC-API-01: Mã sản phẩm không tồn tại

Mở `http://localhost:8000/api/products/9999999999`.

**Kết quả mong đợi:** trả HTTP 404 có JSON lỗi; không trả HTTP 500.

## 7. Kịch bản giọng nói

### TC-VOICE-01: Câu tiếng Việt rõ ràng

**Thao tác:** nói `Tìm áo thun nam màu trắng dưới một triệu`.

**Kết quả mong đợi:**

- Whisper trả transcript gần đúng nội dung đã nói.
- Transcript được đưa vào cùng pipeline tìm kiếm text.
- State nhận diện đúng category, gender, color và giá.

Nếu lỗi chỉ xảy ra ở bước transcript, kiểm tra `OPENAI_API_KEY`, microphone, định dạng audio và endpoint `/api/transcribe`; không quy lỗi cho Retriever.

## 8. Hiệu năng

### TC-PERF-01: Cold start

1. Khởi động lại backend.
2. Thực hiện truy vấn text đầu tiên.
3. Upload ảnh lần đầu.

**Ngưỡng tham khảo khi chạy CPU:**

- Text đầu tiên: nên hoàn thành trong 30 giây.
- Nhận diện ảnh đầu tiên: nên hoàn thành trong 30 giây.
- Không được hết RAM hoặc làm backend tự tắt.

### TC-PERF-02: Warm request

Lặp lại đúng truy vấn và ảnh của TC-PERF-01.

**Kết quả mong đợi:** nhanh hơn lần đầu. Nếu mọi request đều mất trên 20–30 giây, kiểm tra model singleton, cache và việc model có bị nạp lại ở mỗi request hay không.

## 9. Bảng chẩn đoán nhanh

| Triệu chứng | Tầng cần kiểm tra đầu tiên |
|---|---|
| Chip/category/color sai ngay sau khi nhập | `IntentExtractor`, `EntityNormalizer` |
| State đúng nhưng sản phẩm vi phạm gender/giá | `CandidateRetriever`, SQL filter |
| State đúng, không có kết quả dù dữ liệu chắc chắn tồn tại | Ngưỡng similarity, không gian embedding, pgvector |
| Text search rất kém nhưng image search tốt | Text embedding hoặc mô tả sản phẩm |
| Image search không đưa chính ảnh catalog lên gần đầu | FashionSigLIP, preprocessing, vector index |
| Không phát hiện hoặc crop sai món đồ | OWL-ViT, score threshold, tọa độ box |
| Sản phẩm đúng nhưng ảnh 404 | `image_path`, thư mục `data/images`, static mount |
| Lượt sau làm mất điều kiện lượt trước | `StateManager`, `session_id` |
| `giống số 1` trỏ sai sản phẩm | `SESSION_PREVIOUS_RESULTS`, reference ordinal |
| Lần nào cũng nạp model lại | Singleton hoặc vòng đời process Uvicorn |
| Chỉ voice lỗi | Whisper API, audio MIME, API key |
| Backend trả kết quả nhưng frontend không hiển thị | Mapping response frontend, CORS, tên field schema |

## 10. Mẫu ghi nhận kết quả

| Test ID | Trạng thái | Thời gian | Số kết quả | Kết quả thực tế / lỗi | Mức độ |
|---|---|---:|---:|---|---|
| TC-TXT-01 | Chưa chạy |  |  |  |  |
| TC-TXT-02 | Chưa chạy |  |  |  |  |
| TC-TXT-03 | Chưa chạy |  |  |  |  |
| TC-TXT-04 | Chưa chạy |  |  |  |  |
| TC-TXT-05 | Chưa chạy |  |  |  |  |
| TC-TXT-06 | Chưa chạy |  |  |  |  |
| TC-TXT-07 | Chưa chạy |  |  |  |  |
| TC-TXT-08 | Chưa chạy |  |  |  |  |
| TC-CONV-01 | Chưa chạy |  |  |  |  |
| TC-CONV-02 | Chưa chạy |  |  |  |  |
| TC-CONV-03 | Chưa chạy |  |  |  |  |
| TC-CONV-04 | Chưa chạy |  |  |  |  |
| TC-CONV-05 | Chưa chạy |  |  |  |  |
| TC-IMG-01 | Chưa chạy |  |  |  |  |
| TC-IMG-02 | Chưa chạy |  |  |  |  |
| TC-IMG-03 | Chưa chạy |  |  |  |  |
| TC-IMG-04 | Chưa chạy |  |  |  |  |
| TC-IMG-05 | Chưa chạy |  |  |  |  |
| TC-UI-01 | Chưa chạy |  |  |  |  |
| TC-UI-02 | Chưa chạy |  |  |  |  |
| TC-API-01 | Chưa chạy |  |  |  |  |
| TC-VOICE-01 | Chưa chạy |  |  |  |  |
| TC-PERF-01 | Chưa chạy |  |  |  |  |
| TC-PERF-02 | Chưa chạy |  |  |  |  |

## 11. Phân loại mức độ lỗi

- **Blocker:** backend không khởi động, database mất dữ liệu, toàn bộ search không dùng được.
- **Critical:** text search hoặc image search luôn lỗi; bộ lọc giá/gender trả kết quả sai nghiêm trọng.
- **Major:** một nhóm truy vấn, hội thoại hoặc nhận diện ảnh hoạt động sai nhưng còn đường khác sử dụng được.
- **Minor:** lỗi thông báo, chip, ảnh phụ, sắp xếp hoặc hiệu năng chưa tốt.
- **Cosmetic:** lỗi giao diện không ảnh hưởng kết quả và thao tác.

