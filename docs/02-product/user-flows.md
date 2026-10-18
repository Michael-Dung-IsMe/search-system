# Kịch Bản & Luồng Tương Tác Người Dùng (User Flows)

Tài liệu này thuyết minh chi tiết 4 kịch bản người dùng cốt lõi đại diện cho trải nghiệm tìm kiếm thời trang đa phương thức tương tác.

---

## 1. Luồng 1: Tìm Kiếm Bằng Ảnh Phối Đồ (Object-Aware Visual Search)

*Bối cảnh:* Người dùng lướt mạng xã hội thấy một bức ảnh phối đồ phong cách mùa đông và muốn tìm mua chiếc áo khoác blazer trong ảnh đó.

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as Lookbook Studio (Next.js)
    participant Core as Backend (OWL-ViT + SigLIP)
    participant DB as PostgreSQL + pgvector

    User->>UI: Bấm biểu tượng Camera & Upload ảnh outfit
    UI->>Core: Gửi ảnh lên POST /api/detect
    Core-->>UI: Trả về 4 boxes: [Top: Blazer 92%, Pants: Jeans 88%, Shoes: Boots 85%, Bag 79%]
    UI->>User: Mở ObjectSelectModal, hiển thị khung viền tương tác quanh từng món đồ
    User->>UI: Click chọn hộp "Blazer (Top)" và bấm "Tìm kiếm món này"
    UI->>Core: Gửi POST /api/search kèm vùng crop_box
    Core->>DB: Trích xuất vector ảnh crop và truy vấn pgvector HNSW
    DB-->>Core: Top-50 mẫu áo khoác blazer tương tự
    Core-->>UI: Danh sách sản phẩm kèm điểm tương đồng thị giác
    UI->>User: Hiển thị lưới áo blazer kèm huy hiệu "Khớp thị giác 91%"
```

---

## 2. Luồng 2: Tìm Kiếm Bằng Giọng Nói Tiếng Việt (Voice-Only Search)

*Bối cảnh:* Người dùng đang di chuyển hoặc không tiện gõ phím, muốn tìm nhanh trang phục công sở.

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as SearchBar (Web Audio API)
    participant Core as SpeechTranscriber (Whisper)
    participant NLU as IntentExtractor (OpenAI)
    participant DB as PostgreSQL + pgvector

    User->>UI: Nhấn và giữ biểu tượng Microphone
    User->>UI: Nói: "Tìm cho mình áo sơ mi trắng công sở nam dưới 600 ngàn"
    UI->>UI: Tự động ngắt sau 5 giây hoặc khi bấm dừng
    UI->>Core: Gửi file âm thanh WebM lên POST /api/transcribe
    Core-->>UI: Text nhận diện: "Tìm cho mình áo sơ mi trắng công sở nam dưới 600 ngàn"
    UI->>NLU: Gửi câu text sang POST /api/search
    NLU-->>Core: Intent: [category="Shirt", color="White", gender="Menswear", max_price=600000]
    Core->>DB: Truy vấn kết hợp SQL WHERE (price <= 600k) + vector nhúng
    DB-->>Core: Danh sách áo sơ mi trắng
    Core-->>UI: Kết quả tìm kiếm + Các thẻ chip ["Loại: Áo", "Màu: Trắng", "Giá ≤ 600k"]
    UI->>User: Hiển thị danh sách sản phẩm khớp yêu cầu
```

---

## 3. Luồng 3: Tinh Chỉnh Hội Thoại Đa Lượt (Conversational Refinement)

*Bối cảnh:* Người dùng tiếp tục tinh chỉnh từ kết quả của Luồng 2 mà không xóa bộ lọc cũ.

- **Lượt 1 (Hiện tại)**: Đang hiển thị áo sơ mi trắng nam dưới 600k.
- **Lượt 2 (Thu hẹp ngân sách)**:
  - Người dùng gõ vào thanh dính ở chân trang (`StickyRefineBar`): *"Tìm cái nào rẻ hơn nữa, dưới 400k thôi"*.
  - Hệ thống tự động hợp nhất: Giữ nguyên `category="Shirt"`, `color="White"`, `gender="Menswear"`; cập nhật `max_price=400000`.
  - Kết quả cập nhật tức thì, danh sách sản phẩm giá từ 200k - 400k được đưa lên đầu.
- **Lượt 3 (Đổi màu sắc & phong cách)**:
  - Người dùng gõ: *"Đổi sang màu đen hoặc xanh navy đi tiệc"*.
  - Hệ thống tự động ghi đè: `color="Dark Blue"`, thêm `style="party"`.
  - Kết quả đổi sang các mẫu áo màu tối thanh lịch phục vụ dạ tiệc.

---

## 4. Luồng 4: Tương Tác Gỡ Bỏ Bộ Lọc Trực Quan Qua Chips Bar

*Bối cảnh:* Người dùng nhận thấy việc giới hạn giá khiến nhiều mẫu đẹp bị ẩn đi, muốn bỏ giới hạn giá nhưng vẫn giữ màu sắc và danh mục.

```mermaid
sequenceDiagram
    autonumber
    actor User as Người dùng
    participant UI as StateChipsBar Component
    participant API as FastAPI Router
    participant Core as StateManager & SoftReranker

    User->>UI: Click nút [✕] trên thẻ chip "Giá ≤ 400k"
    UI->>API: Gửi DELETE /api/search/{session_id}/constraint?chip_id=max_price:400000
    API->>Core: StateManager.remove_constraint(state, "max_price:400000")
    Note over Core: max_price được đặt lại thành None.<br/>Giữ nguyên vector ảnh và các chip khác.
    Core->>Core: Tái xếp hạng lại ứng viên với vector đã lưu trong bộ đệm
    Core-->>API: Danh sách sản phẩm mới mở rộng
    API-->>UI: SearchResponse (Độ trễ < 20ms)
    UI->>User: Cập nhật lưới sản phẩm mượt mà, chip giá biến mất
```
