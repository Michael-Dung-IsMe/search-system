# Đặc Tả Bộ Dữ Liệu Thời Trang H&M 5.000 Sản Phẩm (Dataset Specification)

Tài liệu này thuyết minh nguồn gốc dữ liệu, chiến lược chọn mẫu phân tầng (*Stratified Sampling*), quy chuẩn làm sạch và cấu trúc bảng dữ liệu phục vụ huấn luyện và đánh giá hệ thống tìm kiếm thời trang đa phương thức.

---

## 1. Nguồn Gốc Bộ Dữ Liệu Gốc

Dữ liệu được khai thác từ cuộc thi chính thức của tập đoàn bán lẻ thời trang quốc tế H&M trên Kaggle: **H&M Personalized Fashion Recommendations**.
- Tổng quy mô tập dữ liệu gốc: hơn **105.000 sản phẩm thời trang** (`articles.csv`) cùng thư mục ảnh độ phân giải cao (`images/`).
- Do đặc thù môi trường học tập và tài nguyên phần cứng giới hạn (GPU 6GB VRAM, RAM 16GB), việc lập chỉ mục toàn bộ 105.000 sản phẩm sẽ gây quá tải bộ nhớ và tốn hàng chục giờ tính toán. Do đó, hệ thống áp dụng kỹ thuật **Chọn mẫu phân tầng (Stratified Sampling)** để trích xuất tập dữ liệu đại diện gồm đúng **5.000 sản phẩm**.

---

## 2. Chiến Lược Phân Tầng (Stratified Sampling Strategy)

Hàm `stratified_sample()` trong `scripts/sample_dataset.py` thực hiện chọn mẫu theo 2 chiều phân tầng độc lập:

### 2.1. Phân tầng theo Giới tính (Gender Distribution)
| Giới tính | Tỷ lệ mục tiêu | Số lượng sản phẩm | Ghi chú |
|---|:---:|:---:|---|
| **Nữ (Ladieswear)** | 60% | 3.000 | Phù hợp với hành vi tiêu dùng thời trang nữ áp đảo trên thị trường thương mại điện tử |
| **Nam (Menswear)** | 40% | 2.000 | Đảm bảo tính đa dạng mẫu cho trang phục nam giới |
| **TỔNG** | **100%** | **5.000** | |

### 2.2. Phân tầng theo Nhóm Danh mục Trang phục (Category Distribution)
| Nhóm danh mục (`group_name`) | Tỷ lệ mục tiêu | Số lượng sản phẩm | Danh mục con tiêu biểu (`sub_category`) |
|---|:---:|:---:|---|
| **Garment Upper body** (Áo) | 40% | 2.000 | T-shirt, Shirt, Blouse, Sweater, Hoodie, Jacket, Blazer, Cardigan |
| **Garment Lower body** (Quần) | 25% | 1.250 | Trousers, Jeans, Shorts, Skirt, Leggings |
| **Dresses** (Váy đầm) | 15% | 750 | Dress, Jumpsuit, Playsuit |
| **Shoes** (Giày dép) | 10% | 500 | Sneakers, Boots, Sandals, Loafers, Heels |
| **Bags** (Túi xách) | 5% | 250 | Backpack, Handbag, Tote bag, Shoulder bag |
| **Accessories** (Phụ kiện) | 5% | 250 | Belt, Hat, Cap, Scarf, Sunglasses |
| **TỔNG** | **100%** | **5.000** | |

---

## 3. Cấu Trúc Bảng Dữ Liệu (`data/sample_articles.csv`)

Mỗi bản ghi sản phẩm trong tập dữ liệu 5.000 mẫu gồm các thuộc tính chuẩn hóa:

| Tên cột | Kiểu dữ liệu | Ví dụ | Ý nghĩa nghiệp vụ |
|---|---|---|---|
| `article_id` | `VARCHAR(10)` | `"0108775015"` | Khóa chính duy nhất đại diện cho từng biến thể sản phẩm |
| `product_code` | `VARCHAR(7)` | `"0108775"` | Mã dòng sản phẩm cha |
| `prod_name` | `VARCHAR(255)` | `"Strap top"` | Tên thương mại của sản phẩm |
| `price_vnd` | `INT` | `299000` | Giá niêm yết bán lẻ quy đổi sang Việt Nam Đồng |
| `gender` | `VARCHAR(20)` | `"Ladieswear"` | Giới tính đối tượng sử dụng |
| `color_code` | `VARCHAR(10)` | `"10"` | Mã màu chuẩn của H&M |
| `color_name` | `VARCHAR(50)` | `"White"` | Tên màu sắc tiếng Anh chuẩn hóa |
| `group_name` | `VARCHAR(100)` | `"Garment Upper body"` | Nhóm danh mục lớn (1 trong 6 nhóm phân tầng) |
| `sub_category` | `VARCHAR(100)` | `"Top"` | Danh mục chi tiết cụ thể |
| `detail_desc` | `TEXT` | `"Jersey top with narrow shoulder straps."` | Đoạn văn bản mô tả chất liệu và chi tiết thiết kế |
| `image_path` | `VARCHAR(255)` | `"images/0108775015.jpg"` | Đường dẫn tương đối trỏ đến file ảnh JPEG của sản phẩm |
| `image_hash` | `VARCHAR(32)` | `"4f5d2e..."` | Mã băm MD5 của ảnh phục vụ bộ đệm cache |

---

## 4. Quy Chuẩn Giá Tiền Việt Nam Đồng (VND Pricing Rules)

Để phản ánh thị trường bán lẻ thời trang Việt Nam thực tế, giá gốc (tính bằng hệ số float từ H&M) được hàm `generate_vnd_price()` quy đổi theo nguyên tắc:
1. **Khoảng giá:** Dao động từ **149.000 VNĐ** đến **2.490.000 VNĐ**.
2. **Quy tắc làm tròn:**
   - Dưới 500.000 VNĐ: Làm tròn theo bước giá 50.000 VNĐ (ví dụ: 199.000đ, 299.000đ, 349.000đ, 499.000đ).
   - Trên 500.000 VNĐ: Làm tròn theo bước giá 100.000 VNĐ (ví dụ: 699.000đ, 899.000đ, 1.290.000đ).
3. **Phân phối giá theo danh mục:** Áo thun basic tập trung ở mức 199k - 399k; Áo khoác da, Blazer dạ tiệc và Giày boot tập trung ở mức 899k - 2.190k.
