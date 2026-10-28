# Kịch bản kiểm thử tay cho module Search

Mục tiêu là đánh giá chất lượng intent, hard filter, vector retrieval, multimodal search và cách frontend hiển thị kết quả. Mỗi thao tác tìm kiếm là một request độc lập; request sau không được kế thừa điều kiện request trước.

## Cách quan sát

Mở backend bằng Uvicorn và theo dõi:

- `intent_extractor`: JSON intent sau LLM và backend reconciliation.
- `retriever`: số kết quả Phase 1/Phase 2 và ngưỡng similarity.
- HTTP status của `/api/search`.
- Tab Network của trình duyệt: `search_state`, `query_type`, `match_type`, `final_score`.

Ghi cho mỗi case: input, intent thực tế, số exact/similar result, top 5 sản phẩm, thời gian và nhận xét.

## Text search

| ID | Input | Kỳ vọng |
|---|---|---|
| T01 | `Tìm quần màu hồng` | Category `Pants`; chỉ Trousers/Shorts; không có giày hồng |
| T02 | `Tìm quần short màu trắng dưới 1 triệu` | `Shorts`, `White`, `max_price=1000000` |
| T03 | `Tìm quần đùi ngắn màu đen` | Nhận dạng `Shorts` |
| T04 | `Tìm quần dài màu xanh` | Nhận dạng `Trousers` |
| T05 | `Tìm áo sơ mi có giá 199.000 đồng` | Không hiểu “đồng” thành màu Bronze/Copper |
| T06 | `Tìm áo đen nhưng không phải len` | Có màu Black và loại trừ wool/knit phù hợp mapping |
| T07 | `Tìm giày thể thao nữ dưới 800k` | Category giày cụ thể, `Ladieswear`, đúng giá |
| T08 | `Xin chào, bạn có khỏe không?` | `response_type=conversation`, không trả sản phẩm |
| T09 | `Xin chào, tìm giúp tôi áo khoác đen` | `product_search`, không bị phân loại thành chat |
| T10 | `Tìm sản phẩm màu cầu vồng` | Không bịa color code không có trong taxonomy |

## Request độc lập

Thực hiện liên tiếp:

1. `Tìm áo sơ mi trắng dưới 500k`.
2. `Tìm quần đen`.

Kỳ vọng request thứ hai:

- Category chỉ là quần.
- Color là Black.
- `max_price` là `null`.
- Request/response không có `session_id`, `turn_index` hoặc `active_chips`.
- Không có thanh `Tinh chỉnh thêm` ở cuối màn hình.

## Voice search

| ID | Nội dung nói | Kỳ vọng |
|---|---|---|
| V01 | `Tìm áo sơ mi trắng dưới năm trăm nghìn` | Transcript đúng; intent đúng category, màu và giá |
| V02 | `Tìm quần đùi màu hồng` | `Shorts`, không phải `Trousers` |
| V03 | `Giới thiệu cho tôi một số mẫu áo` | Product search, không phải chitchat |
| V04 | Nói nhỏ, có tiếng ồn nền | Ghi nhận transcript và lỗi nhận dạng thực tế |

Response của search sau transcription phải có `query_type=voice`. Ghi âm tự dừng sau tối đa 20 giây.

## Image search

| ID | Input | Kỳ vọng |
|---|---|---|
| I01 | Ảnh chỉ có một chiếc quần | Detector khoanh vùng quần; search dùng `image_embedding` |
| I02 | Outfit có áo và quần | Hiện nhiều box, có thể chọn từng vật thể |
| I03 | Ảnh áo hoodie | Box có thể chỉ ghi nhãn chung “Áo”; category catalog chi tiết được suy từ image neighbors |
| I04 | Ảnh hỏng hoặc không phải ảnh | HTTP 400 và thông báo rõ ràng |
| I05 | Ảnh sản phẩm gần giống một ảnh catalog | Top results có image similarity hợp lý |

Phần trăm cạnh bounding box là confidence của OWL-ViT. Nhãn `% khớp ảnh` trên product card chỉ được hiện khi `query_type=image`.

## Image + text

| ID | Ảnh | Text trong cùng lần gửi | Kỳ vọng |
|---|---|---|---|
| M01 | Quần dài đen | `quần này màu trắng dưới 1 triệu` | Dùng ảnh cho hình dáng; lọc White và giá |
| M02 | Quần dài | `tìm quần short giống chiếc này, màu hồng` | Category cụ thể `Shorts` từ text ghi đè suy luận ảnh |
| M03 | Quần short | `quần này màu xanh` | Text chung không ép `Trousers`; ảnh hỗ trợ suy `Shorts` |
| M04 | Outfit nhiều món | Chọn box áo + `màu trắng` | Chỉ crop áo rồi áp điều kiện White |

Ảnh và text phải cùng nằm trong một request `/api/search`. Không gửi text ở request sau với kỳ vọng backend nhớ ảnh trước.

## Facet sidebar

1. Tìm `áo thun trắng dưới 500k`.
2. Chọn màu hồng trong sidebar.
3. Mở tab Network và xem request mới.

Kỳ vọng `query_text` mới chứa đầy đủ category, màu hồng và mức giá. Bỏ một facet khiến frontend gửi lại toàn bộ các facet còn lại.

## Phase 1 và Phase 2

- Chọn query có sản phẩm khớp metadata để xác nhận log `Phase 1: Found ...`.
- Chọn tổ hợp màu/giá không tồn tại để xác nhận Phase 2 chạy.
- Category phải được giữ khi relaxation; `quần màu hồng` không được nới sang giày màu hồng.
- Kết quả dưới ngưỡng text `0.58` hoặc image `0.65` không được đưa vào Phase 2.

## Tiêu chí phát hiện vấn đề

| Hiện tượng | Khu vực kiểm tra |
|---|---|
| Intent sai dù từ xuất hiện rõ trong câu | `extractor.py`, `normalizer.py` |
| Intent đúng nhưng sai loại sản phẩm | `retriever.py`, taxonomy trong DB |
| Image category sai | image neighbors, vector catalog, `detector.py` |
| Thứ tự kết quả thiếu hợp lý | `reranker.py` và chất lượng vector |
| Request sau giữ điều kiện cũ | `page.tsx` hoặc API contract; backend không được có session cache |
| Facet làm mất các facet khác | `buildFacetQuery()` trong `page.tsx` |
| Text/voice hiện `% khớp ảnh` | `query_type`, `ProductGrid.tsx`, `ProductCard.tsx` |
| Kết quả lạ khi DB lỗi | CSV fallback và dataset `data/sample_articles.csv` |
