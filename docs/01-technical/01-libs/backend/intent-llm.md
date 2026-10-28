# OpenAI SDK: Trích Xuất Ý Định & Ràng Buộc Bằng Mô Hình Ngôn Ngữ

## 1. Thông tin tổng quan & Phiên bản
- **Tên package:** `openai`
- **Phiên bản:** `openai>=1.30.0`
- **Model phục vụ:** `gpt-4o-mini`
- **Cơ chế gọi:** OpenAI Chat Completions API với tính năng **Structured Outputs (`response_format={"type": "json_schema"}`)**.
- **Vai trò trong hệ thống:** Tầng Hiểu Ngôn Ngữ Tự Nhiên (Natural Language Understanding - NLU), phân tích câu truy vấn tiếng Việt phức tạp của người dùng để bóc tách thành các thuộc tính lọc có cấu trúc.

## 2. Cài để làm gì?
- Tiếp nhận câu truy vấn tự nhiên (từ gõ text hoặc từ audio sau khi qua Speech-to-Text), ví dụ:
  *"Tìm cho anh cái áo khoác blazer nam màu xanh navy dạ tiệc dưới 1 triệu rưỡi nhưng không lấy chất liệu nỉ"*.
- Bóc tách chuẩn xác thành đối tượng JSON cấu trúc theo schema `QueryIntent`:
  - `category`: `"Jacket / Blazer"`
  - `color`: `"Dark Blue"`
  - `gender`: `"Menswear"`
  - `max_price`: `1500000`
  - `style`: `"formal / evening"`
  - `exclude_materials`: `["nỉ", "fleece"]`
  - `normalized_query`: `"navy blue formal blazer jacket"` (câu tiếng Anh chuẩn phục vụ embedder)
- Hiểu ngữ cảnh hội thoại bổ sung (Turn Refinements): *"rẻ hơn nữa"*, *"đổi sang màu be"*, *"bỏ giới hạn giá đi"*.

## 3. Vì sao chọn & Phương án thay thế (Trade-offs)
- **Lý do lựa chọn:**
  - **Structured Outputs chuẩn 100%**: Cam kết kết quả trả về tuân thủ tuyệt đối Pydantic JSON Schema, không bao giờ bị lỗi vỡ định dạng JSON.
  - Mô hình `gpt-4o-mini` có độ trễ cực thấp (~350ms), chi phí cực rẻ ($0.15 / 1M input tokens), và khả năng hiểu tiếng Việt 3 miền xuất sắc.
  - Giảm tải hoàn toàn việc tính toán NLU trên GPU nội bộ (để dành 100% VRAM 6GB cho OWL-ViT và SigLIP).
- **Phương án thay thế đã cân nhắc:**
  - *Regex / Rule-based*: Chỉ xử lý được câu mẫu đơn giản, hoàn toàn thất bại khi gặp câu phủ định ("không phải da"), tiếng lóng ("bận đi quẩy"), hoặc ngữ cảnh đa lượt.
  - *Llama-3-8B nội bộ*: Đòi hỏi tối thiểu 5.5GB VRAM (kể cả khi đã lượng tử hóa 4-bit), sẽ làm sập máy khi chạy cùng các model khác trên GTX 1660 Ti.

## 4. Vị trí sử dụng trong mã nguồn
| File mã nguồn | Vai trò / Logic cụ thể | Đường dẫn trực tiếp |
|---|---|---|
| `backend/core/extractor.py` | Class `IntentExtractor`, hàm `extract()`, `_extract_with_openai()`, `_extract_with_rules()` | [extractor.py](../../../../backend/core/extractor.py) |
| `backend/routes/search_routes.py` | Bóc tách ý định và tạo `SearchState` mới cho request `/api/search` | [search_routes.py](../../../../backend/routes/search_routes.py) |

## 5. Trạng thái thực tế
- **Mức độ tích hợp:** Hoạt động chính thức.
- **Cơ chế Fallback 3 Tầng Siêu Bền Vững:**
  1. *Tầng 1*: Gọi OpenAI `gpt-4o-mini` qua Structured Outputs.
  2. *Tầng 2*: Nếu mạng lỗi hoặc hết quota API, tự động fallback sang `_extract_with_gemini` (nếu cấu hình API key).
  3. *Tầng 3*: Nếu hoàn toàn offline, tự động kích hoạt `_extract_with_rules` kết hợp bộ từ điển `EntityNormalizer` (xử lý regex màu sắc, giá tiền, danh mục cơ bản) mà không làm gián đoạn trải nghiệm người dùng.

## 6. Lưu ý kỹ thuật & Hiệu năng
- **Bảo mật API Key:** Khóa `OPENAI_API_KEY` được nạp qua file `.env`, tuyệt đối không commit lên Git.
- **System Prompt Căn Chỉnh:** Prompt được tinh chỉnh chuyên biệt cho thời trang Việt Nam, chứa các ví dụ chuẩn hóa phương ngữ (*bận $\to$ mặc*, *chiệu $\to$ triệu*, *quần tà lỏn $\to$ quần shorts*).
