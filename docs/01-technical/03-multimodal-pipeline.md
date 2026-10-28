# Pipeline Tìm Kiếm Đa Phương Thức (Multimodal Search Pipeline)

Tài liệu này thuyết minh chi tiết luồng xử lý dữ liệu 6 bước của hệ thống tìm kiếm thời trang đa phương thức, nguyên lý kết hợp (Multimodal Fusion), và công thức xếp hạng đa tín hiệu.

---

## 1. Tổng Quan Luồng Xử Lý 6 Bước

Hệ thống hợp nhất 3 kênh nhập liệu (Hình ảnh, Giọng nói, Văn bản tự do) thành một **Query Intent** duy nhất và xử lý qua 6 giai đoạn liên hoàn:

```text
Image + Voice Audio + Text
           │
           ▼
[GIAI ĐOẠN 1: TIẾP NHẬN & PHÂN NHÁNH ĐẦU VÀO]
   ├─ Audio   ──► SpeechTranscriber (OpenAI gpt-transcribe) ──► Văn bản tiếng Việt
   ├─ Ảnh Gốc ──► ObjectDetector (OWL-ViT FP16)   ──► Bounding Boxes & Polygons
   └─ Text    ──► Chuỗi mô tả người dùng
           │
           ▼
[GIAI ĐOẠN 2: BÓC TÁCH Ý ĐỊNH & CHUẨN HÓA THỰC THỂ]
   ├─ EntityNormalizer: Sửa phương ngữ 3 miền, chuẩn hóa từ điển màu sắc và giá VND
   └─ IntentExtractor (OpenAI gpt-4o-mini Structured JSON Outputs)
           │
           ▼
[GIAI ĐOẠN 3: TẠO SEARCHSTATE CHO REQUEST HIỆN TẠI]
   ├─ Tạo mới SearchState từ QueryIntent, không kế thừa request trước
   ├─ Xử lý các điều kiện phủ định ("không phải da", "loại trừ màu đen")
   └─ Gắn reference_article_id khi tìm từ một thẻ sản phẩm
           │
           ▼
[GIAI ĐOẠN 4: TRÍCH XUẤT VECTOR NHÚNG HYBRID (HYBRID EMBEDDER)]
   ├─ Nhánh Ảnh Crop: Sinh vector thị giác 768 chiều (Marqo-fashionSigLIP Vision Encoder)
   └─ Nhánh Text/Voice: Sinh vector ngữ nghĩa 768 chiều (OpenAI text-embedding-3-small, dim=768)
           │
           ▼
[GIAI ĐOẠN 5: TRUY VẤN LAI PHÂN VÙNG THEO KHÔNG GIAN (DUAL-SPACE PARTITIONED RETRIEVAL)]
   ├─ PostgreSQL Hard Constraints: SQL WHERE (price <= max_price, gender, category)
   ├─ pgvector HNSW ANN Search (Phân tách cột theo phương thức):
   │    ├─ Truy vấn Text/Voice: (p.text_embedding <=> text_vector) ORDER BY distance ASC
   │    └─ Truy vấn Ảnh Crop:   (p.image_embedding <=> img_vector) ORDER BY distance ASC
   └─ Phân vùng kết quả:
        ├─ Phân vùng 1: Exact Matches (Khớp chính xác cả thuộc tính cứng lẫn vector)
        └─ Phân vùng 2: Similar Recommendations (Gợi ý tương tự nới lỏng tiêu chí)
           │
           ▼
[GIAI ĐOẠN 6: TÁI XẾP HẠNG ĐA TÍN HIỆU & SINH HUY HIỆU GIẢI THÍCH (SOFT RERANKER)]
   ├─ Chấm điểm mềm (Phong cách, Dịp mặc, Chất liệu, Danh mục con)
   ├─ Áp dụng điểm phạt (Penalties) nếu vi phạm điều kiện loại trừ
   └─ Sinh Explainable Badges trực quan: "Khớp 95% phong cách dạ hội", "Vải cotton thoáng mát"
```

---

## 2. Chi Tiết Từng Giai Đoạn

### Giai đoạn 1: Tiếp nhận & Phân nhánh đầu vào
- **Nhánh Giọng nói**: Audio blob được gửi lên `POST /api/transcribe`, chuyển qua OpenAI `gpt-transcribe` với `language=vi` để tạo ra chuỗi text tiếng Việt.
- **Nhánh Thị giác**: Ảnh phối đồ toàn thân được đưa qua `ObjectDetector.detect()`. Mô hình OWL-ViT phát hiện các thành phần trang phục kèm điểm tự tin (*confidence score*), trả về tọa độ chuẩn hóa và contour polygon.
- **Nhánh Cắt ảnh**: Khi người dùng chọn một vùng món đồ, ảnh được crop theo tỷ lệ chuẩn hóa và lưu tạm vào `data/uploads/`.

### Giai đoạn 2: Bóc tách ý định & Chuẩn hóa thực thể
- **Sửa phương ngữ & từ địa phương**: `EntityNormalizer.normalize_phonetics()` chuyển đổi phát âm 3 miền:
  - *dày da $\rightarrow$ giày da*
  - *bận đi làm $\rightarrow$ mặc đi làm*
  - *chiệu $\rightarrow$ triệu*
- **Trích xuất JSON cấu trúc**: `IntentExtractor` gọi OpenAI `gpt-4o-mini` với schema định sẵn để bóc tách thành đối tượng `QueryIntent`.

### Giai đoạn 3: Tạo SearchState cho request
- `/api/search` tạo một `SearchState` mới từ toàn bộ trường của `QueryIntent` hiện tại.
- Không có `session_id`, `turn_index`, merge intent hoặc bộ nhớ vector theo phiên.
- Ảnh và text cần kết hợp phải được gửi trong cùng request. Khi người dùng đổi facet, frontend ghép toàn bộ facet đang chọn thành một query hoàn chỉnh rồi gửi lại.
- `search_audit.persist_search()` chỉ ghi lịch sử phục vụ audit; nó không làm trạng thái cho request sau.

### Giai đoạn 4: Trích xuất vector nhúng Hybrid (Dual-space Embedding)
Hệ thống phân tách luồng trích xuất vector theo phương thức đầu vào để tối ưu hóa đặc thù ngữ nghĩa và thị giác:
- **Nhánh Thị giác (Image Search)**:
  - Sử dụng mô hình `Marqo/marqo-fashionSigLIP` (Vision Transformer `ViT-B-16-SigLIP`).
  - Nhận ảnh crop từ outfit của người dùng, đưa qua bộ tiền xử lý và mạng trích xuất đặc trưng để tạo vector thị giác 768 chiều.
- **Nhánh Văn bản & Giọng nói (Text/Voice Search)**:
  - Sử dụng mô hình OpenAI `text-embedding-3-small` với tham số `dimensions=768` (Matryoshka representation learning).
  - Nhận câu truy vấn người dùng (tiếng Việt hoặc tiếng Anh đã qua chuẩn hóa), sinh ra vector ngữ nghĩa 768 chiều.
  - Tích hợp cơ chế fallback cục bộ: Tự động chuyển về SigLIP Text Encoder nếu không có API key hoặc mạng gián đoạn.
- Cả hai vector đầu ra đều có độ dài 768 chiều và được chuẩn hóa L2 norm ($\|v\|_2 = 1.0$), tương thích tuyệt đối với schema CSDL.

### Giai đoạn 5: Truy vấn lai phân vùng theo không gian (Dual-space Partitioned Hybrid Retrieval)
Hệ thống thực hiện truy vấn tối ưu chia làm 2 phân vùng độc lập, tự động định tuyến cột vector tương ứng:
- **Định tuyến cột vector mục tiêu**:
  - Khi người dùng tìm kiếm bằng Text hoặc Voice: So sánh độ tương đồng với cột `p.text_embedding` (đã được tạo bởi OpenAI `text-embedding-3-small`).
  - Khi người dùng tìm kiếm bằng Ảnh Crop: So sánh độ tương đồng với cột `p.image_embedding` (đã được tạo bởi SigLIP Vision Encoder).
  - Tuyệt đối không so sánh chéo trực tiếp vector OpenAI với vector SigLIP vì hai mô hình nằm ở hai không gian hình học riêng biệt.
1. **Phân vùng Khớp chính xác (Exact Matches)**: Thỏa mãn đồng thời tất cả các Hard Constraints trong SQL WHERE (giới tính, khoảng giá tối đa, màu sắc cơ bản) và lấy top theo khoảng cách vector cosine nhỏ nhất.
2. **Phân vùng Gợi ý tương tự (Similar Recommendations)**: Nếu phân vùng 1 trả về quá ít hoặc không có kết quả, hệ thống tự động nới lỏng các điều kiện lọc cứng để đưa ra các sản phẩm có độ tương đồng cao nhất nhằm tránh trải nghiệm "Trang trắng không có kết quả".

---

## 3. Công Thức Tái Xếp Hạng Đa Tín Hiệu (Multi-Signal Scoring Formula)

Để đảm bảo kết quả phản ánh chân thực mong muốn của người dùng, `SoftReranker` áp dụng công thức chấm điểm đa tín hiệu:

$$\text{FinalScore} = w_{\text{vector}} \cdot S_{\text{vector}} + w_{\text{cat}} \cdot S_{\text{cat}} + w_{\text{color}} \cdot S_{\text{color}} + w_{\text{style}} \cdot S_{\text{style}} - P_{\text{penalty}}$$

Trong đó:
- $S_{\text{vector}} = 1.0 - \text{CosineDistance}$: Độ tương đồng vector thị giác/ngữ nghĩa (thang điểm 0.0 đến 1.0).
- $S_{\text{cat}}$: Điểm khớp danh mục con cụ thể (+0.15 điểm).
- $S_{\text{color}}$: Điểm khớp họ màu sắc mở rộng (+0.10 điểm).
- $S_{\text{style}}$: Điểm khớp phong cách hoặc ngữ cảnh sử dụng (+0.10 điểm).
- $P_{\text{penalty}}$: Điểm phạt nặng nếu sản phẩm chứa chất liệu hoặc đặc điểm nằm trong danh sách loại trừ `exclude_materials` (-0.40 điểm).

---

## 4. Cơ Chế Sinh Huy Hiệu Giải Thích Minh Bạch (Explainable Badges)

Sau khi tính toán điểm số tái xếp hạng, hệ thống tự động sinh các nhãn trực quan gắn vào từng thẻ sản phẩm (`badges: string[]`):
- Khi điểm vector $> 0.85$: Gắn huy hiệu `"Khớp thị giác cao"`.
- Khi khớp tiêu chí vải cotton: Gắn huy hiệu `"Vải cotton"`.
- Khi thỏa mãn mức ngân sách: Gắn huy hiệu `"Giá phù hợp"`.
- Khi sản phẩm nằm trong danh mục dạ tiệc: Gắn huy hiệu `"Dạ hội / Trang trọng"`.

Cơ chế này giúp người dùng hiểu rõ **vì sao AI lại đề xuất sản phẩm này** cho họ.
