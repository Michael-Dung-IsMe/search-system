# Sổ Tay Vận Hành & Khởi Chạy Hệ Thống (Operations Runbook)

Tài liệu này cung cấp hướng dẫn từng bước (Step-by-Step Runbook) để vận hành, khởi chạy, kiểm thử và xử lý sự cố cho hệ thống **Interactive Multimodal Shopping Search Engine**. Hướng dẫn được phân tách rõ ràng cho 2 tình huống:
1. **Nhóm 1: Khởi chạy trên máy hiện tại** (Môi trường phát triển cục bộ đã có sẵn cấu hình và môi trường).
2. **Nhóm 2: Khởi chạy trên thiết bị mới** (Máy tính cá nhân khác, Laptop demo, Máy chủ phòng lab hoặc Máy ảo sạch).

---

## Bảng So Sánh Hai Nhóm Môi Trường

| Tiêu chí | Nhóm 1: Máy Hiện Tại | Nhóm 2: Thiết Bị Khác (Máy Mới) |
|---|---|---|
| **Hệ điều hành** | Windows 11 (PowerShell) | Windows / Ubuntu Linux / macOS |
| **Phần cứng** | Intel Core i7-9750H, NVIDIA GTX 1660 Ti (6GB VRAM), 16GB RAM | CPU 4+ cores, RAM >= 8GB, GPU (Tùy chọn) |
| **Môi trường Python** | Conda env `httt-search-system` (`D:\miniconda3\envs\httt-search-system`) | Cần tạo mới Conda env hoặc Python `venv` (Python 3.10) |
| **Môi trường Frontend** | Node.js 20+, `web/node_modules` đã cài | Cần cài Node.js >= 18 và chạy `npm install` |
| **CSDL PostgreSQL** | Docker container `fashion_search_postgres` (Port `5434`) | Cần kéo Docker image, khởi chạy container và init CSDL |
| **Dữ liệu & Index** | Dữ liệu 5.000 sản phẩm H&M và Vector Hybrid (OpenAI + SigLIP) đã sẵn sàng | Cần nạp dữ liệu từ dump hoặc chạy script `index_products.py` |

---

# NHÓM 1: KHỞI CHẠY TRÊN MÁY HIỆN TẠI

Trên máy tính hiện tại, mọi môi trường ảo, dependencies, models cache và volume dữ liệu đã được cấu hình tối ưu.

### 1.1. Khởi động Cơ sở Dữ liệu (PostgreSQL + pgvector)
Mở một cửa sổ PowerShell tại thư mục gốc dự án:
```powershell
docker compose up -d
```
- **Kiểm tra trạng thái container:**
```powershell
docker ps --filter "name=fashion_search_postgres"
```
Container phải hiển thị trạng thái `Up` và `(healthy)`. Cổng CSDL mở tại `localhost:5434`.

---

### 1.2. Khởi động Backend Server (FastAPI)
Mở cửa sổ terminal thứ hai:
```powershell
# Chạy trực tiếp qua đường dẫn Python Conda của dự án:
D:\miniconda3\envs\httt-search-system\python.exe backend/main.py

# Hoặc kích hoạt môi trường conda trước:
conda activate httt-search-system
python backend/main.py
```
- **Kiểm tra hoạt động:**
  - Backend lắng nghe tại: `http://localhost:8000`
  - Giao diện tài liệu tương tác Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
  - Tài liệu kỹ thuật ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### 1.3. Khởi động Frontend Web (Next.js Lookbook Studio)
Mở cửa sổ terminal thứ ba:
```powershell
cd web
npm run dev
```
- **Kiểm tra hoạt động:**
  - Giao diện người dùng mở tại: [http://localhost:3000](http://localhost:3000)
  - Frontend sẽ tự động kết nối với backend tại `http://localhost:8000/api`.

---

### 1.4. Chạy Bộ Kiểm Thử (Testing & QA)
Khi cần xác thực toàn bộ hệ thống trước khi báo cáo hoặc commit:
```powershell
# 1. Kiểm thử Backend (Toàn bộ 93 test cases, độ phủ code > 80%):
D:\miniconda3\envs\httt-search-system\python.exe -m pytest tests/

# 2. Kiểm thử Frontend (9 test suites Jest & React Testing Library):
cd web
npm test -- --watchAll=false
```

---

### 1.5. Dừng Hệ Thống (Graceful Shutdown)
1. Tại terminal Frontend: Nhấn `Ctrl + C` và gõ `Y` để dừng Next.js dev server.
2. Tại terminal Backend: Nhấn `Ctrl + C` để dừng Uvicorn ASGI server.
3. Dừng CSDL:
```powershell
docker compose down
```
*(Dữ liệu CSDL và chỉ mục vector được lưu an toàn trong Docker Volume `postgres_data`, không bị mất khi hạ container).*

---

# NHÓM 2: KHỞI CHẠY TRÊN THIẾT BỊ KHÁC

Phần này dành cho trường hợp chuyển sang máy tính mới, laptop cá nhân của thành viên khác, máy chấm thi hoặc môi trường phòng lab.

### 2.1. Yêu Cầu Tiên Quyết (Prerequisites)
Thiết bị mới cần được cài đặt sẵn:
1. **Git**: Dùng để clone repository.
2. **Docker & Docker Compose**:
   - Windows / macOS: Cài đặt [Docker Desktop](https://www.docker.com/products/docker-desktop/).
   - Ubuntu / Debian Linux: `sudo apt-get install docker.io docker-compose-v2`.
3. **Python 3.10**:
   - Khuyến nghị sử dụng [Miniconda](https://docs.conda.io/en/latest/miniconda.html) hoặc Python 3.10 chính thức.
4. **Node.js**: Phiên bản LTS 18.x hoặc 20.x ([NodeJS.org](https://nodejs.org/)) kèm theo `npm`.
5. *(Tùy chọn GPU)*: Nếu máy có card đồ họa NVIDIA, cài đặt [NVIDIA Driver](https://www.nvidia.com/drivers) và [CUDA Toolkit 11.8 hoặc 12.x]. Nếu không có GPU, hệ thống tự động chạy trên CPU mà không cần sửa code.

---

### 2.2. Bước 1: Lấy Mã Nguồn & Cấu Hình Biến Môi Trường
```bash
# 1. Clone repository về máy mới
git clone <repository_url> search-system
cd search-system

# 2. Tạo file cấu hình môi trường từ mẫu
cp .env.example .env
```
Mở file `.env` vừa tạo để tùy chỉnh (nếu cần):
```ini
# Cấu hình CSDL PostgreSQL (Mặc định chạy cổng 5434 để tránh trùng cổng 5432)
POSTGRES_HOST=localhost
POSTGRES_PORT=5434
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fashion_search

# Khóa API AI (Tùy chọn):
# OPENAI_API_KEY dùng cho: Intent Extraction (gpt-4o-mini), Speech-to-Text (gpt-transcribe),
# và Text Embedding (text-embedding-3-small, dimensions=768).
# Nếu không điền, text embedding và intent extraction vẫn có fallback cục bộ;
# endpoint Speech-to-Text sẽ báo lỗi cấu hình thay vì trả về một transcript giả.
OPENAI_API_KEY=
GEMINI_API_KEY=

# Cấu hình Embedding & Ngưỡng tương đồng
TEXT_EMBEDDING_MODEL=text-embedding-3-small
THRESHOLD_TEXT=0.45
THRESHOLD_IMAGE=0.65
```

---

### 2.3. Bước 2: Khởi Tạo CSDL & Chỉ Mục Pgvector
Khởi chạy container PostgreSQL với extension pgvector được tích hợp sẵn:
```bash
docker compose up -d
```
Chờ 5-10 giây để container khởi động và thực thi file khởi tạo `backend/db/schema.sql` (tạo 14 bảng dữ liệu, kiểu dữ liệu `vector(768)` và chỉ mục HNSW).
- Kiểm tra container đang chạy:
```bash
docker compose ps
```

---

### 2.4. Bước 3: Thiết Lập Môi Trường Backend Python

#### Lựa chọn A: Dùng Conda (Khuyến nghị cho cả máy có GPU và CPU)
```bash
# Tạo môi trường Python 3.10
conda create -n httt-search-system python=3.10 -y
conda activate httt-search-system

# Cài đặt PyTorch:
# - Đối với máy có GPU NVIDIA (CUDA 12.1):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# - Đối với máy chỉ có CPU:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Cài đặt toàn bộ dependencies của dự án:
pip install -r requirements.txt
```

#### Lựa chọn B: Dùng Python `venv` (Nếu không cài Conda)
```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt virtual environment:
# Trên Windows:
venv\Scripts\activate
# Trên Linux/macOS:
source venv/bin/activate

# Nâng cấp pip và cài đặt thư viện:
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 2.5. Bước 4: Nạp Dữ Liệu Sản Phẩm & Sinh Vector (Lần đầu tiên)
Nếu thiết bị mới chưa có dữ liệu trong CSDL:
```bash
# Chạy script lập chỉ mục 5.000 sản phẩm H&M và tính vector embedding Hybrid (SigLIP cho ảnh + OpenAI cho text):
python scripts/index_products.py
```
> [!NOTE]
> Lần đầu chạy, script sẽ tự động tải weights của mô hình `Marqo/marqo-fashionSigLIP` (~1.8GB) và `google/owlvit-base-patch32` (~600MB) về thư mục cache HuggingFace (`~/.cache/huggingface/hub/`). Quá trình này diễn ra một lần duy nhất. Nếu có `OPENAI_API_KEY`, trường `text_embedding` sẽ được sinh qua OpenAI API (`text-embedding-3-small`, 768 chiều). Nếu không có key, script sẽ tự động fallback sinh vector text qua SigLIP.

---

### 2.6. Bước 5: Cài Đặt & Khởi Động Frontend Web
Mở một cửa sổ terminal mới:
```bash
cd web

# Cài đặt dependencies (React 19, Next.js 16.4, TailwindCSS v4, Lucide React)
npm install

# (Tùy chọn) Nếu backend chạy ở host/cổng khác http://localhost:8000:
# tạo file web/.env.local và thêm: NEXT_PUBLIC_API_URL=http://<ip-or-host>:8000

# Khởi chạy frontend ở chế độ Development:
npm run dev
```

---

### 2.7. Bước 6: Kiểm Tra Sẵn Sàng (Verification & Smoke Test)
1. **Truy cập ứng dụng:**
   - Web Lookbook: [http://localhost:3000](http://localhost:3000)
   - Backend Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
2. **Kiểm tra tính toàn vẹn bằng bộ Unit & Integration Test:**
   ```bash
   # Tại thư mục gốc:
   pytest tests/
   ```
   Kết quả mong đợi: `93 passed in ~40s` (Đạt 100% test cases).

---

# HƯỚNG DẪN XỬ LÝ SỰ CỐ THƯỜNG GẶP (TROUBLESHOOTING)

### 1. Lỗi xung đột cổng (Port Conflict)
- **Hiện tượng:** Docker báo lỗi `bind: address already in use` cho cổng `5434`, hoặc Uvicorn báo lỗi cổng `8000`, hoặc Next.js chuyển sang cổng `3001`.
- **Cách xử lý:**
  - Nếu cổng 5434 bị chiếm: Sửa `POSTGRES_PORT=5435` trong file `.env` và `docker-compose.yml`, sau đó khởi động lại container: `docker compose up -d`.
  - Nếu cổng 8000 bị chiếm: Chạy backend với cổng khác: `python backend/main.py --port 8001`, và tạo file `web/.env.local` với dòng `NEXT_PUBLIC_API_URL=http://localhost:8001`.

### 2. Lỗi tràn bộ nhớ GPU (CUDA Out Of Memory - OOM)
- **Hiện tượng:** Khi chạy trên GPU có ít VRAM (< 4GB), PyTorch báo lỗi `torch.cuda.OutOfMemoryError`.
- **Cách xử lý:**
  - Đặt biến môi trường `CUDA_VISIBLE_DEVICES=""` để ép PyTorch chạy chế độ CPU:
    ```bash
    # Windows PowerShell:
    $env:CUDA_VISIBLE_DEVICES=""
    python backend/main.py

    # Linux / macOS:
    CUDA_VISIBLE_DEVICES="" python backend/main.py
    ```

### 3. Không có khóa OpenAI API Key (`OPENAI_API_KEY`)
- **Hiện tượng:** Người dùng mới không có tài khoản OpenAI hoặc key hết hạn.
- **Cách xử lý:**
  - Không cần lo lắng. Hệ sinh thái đã được thiết kế kiến trúc Fallback đa tầng:
    - Bóc tách ý định: Tự động chuyển sang `EntityNormalizer` kết hợp Rule-based Regex trích xuất đầy đủ Danh mục, Giới tính, Màu sắc, Giá tiền VND và Từ khóa loại trừ.
    - Trích xuất Text Embedding: Tự động chuyển sang sử dụng Text Encoder cục bộ của `Marqo/marqo-fashionSigLIP` (hoặc mock vector khi test), không làm gián đoạn tính năng tìm kiếm văn bản.
    - Nhận diện giọng nói: Tự động dùng bộ mẫu tiếng Việt nội bộ hoặc bộ giải mã thay thế.
  - Toàn bộ 93/93 test cases đều được thiết kế pass mà không phụ thuộc vào kết nối OpenAI ra bên ngoài.

### 4. Lỗi Docker Desktop chưa khởi động
- **Hiện tượng:** Lỗi `error during connect: In the default daemon with... docker.sock`.
- **Cách xử lý:**
  - Mở ứng dụng **Docker Desktop** trên Windows/macOS và đợi biểu tượng chuyển sang màu xanh lá cây (Running), sau đó chạy lại lệnh `docker compose up -d`.

