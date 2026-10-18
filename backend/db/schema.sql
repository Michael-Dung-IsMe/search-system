-- Interactive Multimodal Shopping Search Engine
-- PostgreSQL 16 + pgvector Schema (14-Class UML Model)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Customer Table (Khách hàng)
CREATE TABLE IF NOT EXISTS customer (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    age INT CHECK (age >= 0),
    phone_number VARCHAR(20),
    shipping_address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Category Table (Danh mục sản phẩm)
CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,
    sub_category VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_category_group_sub UNIQUE (group_name, sub_category)
);

-- 3. Product Table (Sản phẩm với Vector Embeddings tích hợp trực tiếp)
CREATE TABLE IF NOT EXISTS product (
    article_id VARCHAR(20) PRIMARY KEY,
    category_id INT NOT NULL REFERENCES category(id) ON DELETE RESTRICT,
    product_code VARCHAR(20) NOT NULL,
    prod_name VARCHAR(255) NOT NULL,
    color_code VARCHAR(20),
    gender VARCHAR(20) NOT NULL,
    price_vnd INT NOT NULL CHECK (price_vnd >= 0),
    detail_desc TEXT,
    image_path VARCHAR(255) NOT NULL,
    image_hash VARCHAR(64),
    image_embedding vector(768),
    text_embedding vector(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. SearchQuery Table (Bảng cha - Truy vấn tìm kiếm)
CREATE TABLE IF NOT EXISTS search_query (
    query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customer(id) ON DELETE SET NULL,
    query_type VARCHAR(20) NOT NULL DEFAULT 'text',
    search_criteria TEXT,
    reference_article_id VARCHAR(20) REFERENCES product(article_id) ON DELETE SET NULL,
    extracted_intent JSONB NOT NULL DEFAULT '{}'::jsonb,
    latency_ms INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. TextQuery Table (Bảng con - Kế thừa SearchQuery qua TPT)
CREATE TABLE IF NOT EXISTS text_query (
    query_id UUID PRIMARY KEY REFERENCES search_query(query_id) ON DELETE CASCADE,
    query_text TEXT NOT NULL
);

-- 6. ImageQuery Table (Bảng con - Kế thừa SearchQuery qua TPT)
CREATE TABLE IF NOT EXISTS image_query (
    query_id UUID PRIMARY KEY REFERENCES search_query(query_id) ON DELETE CASCADE,
    image_reference VARCHAR(255) NOT NULL,
    selected_region VARCHAR(100)
);

-- 7. VoiceQuery Table (Bảng con - Kế thừa SearchQuery qua TPT)
CREATE TABLE IF NOT EXISTS voice_query (
    query_id UUID PRIMARY KEY REFERENCES search_query(query_id) ON DELETE CASCADE,
    transcribe_text TEXT NOT NULL,
    audio_reference VARCHAR(255)
);

-- 8. SearchResult Table (Lưu kết quả tìm kiếm đã hiển thị)
CREATE TABLE IF NOT EXISTS search_result (
    id SERIAL PRIMARY KEY,
    query_id UUID NOT NULL REFERENCES search_query(query_id) ON DELETE CASCADE,
    article_id VARCHAR(20) NOT NULL REFERENCES product(article_id) ON DELETE CASCADE,
    rank INT NOT NULL CHECK (rank >= 1),
    score FLOAT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_search_result_query_article UNIQUE (query_id, article_id)
);

-- 9. Cart Table (Giỏ hàng)
CREATE TABLE IF NOT EXISTS cart (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customer(id) ON DELETE CASCADE,
    query_id UUID REFERENCES search_query(query_id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. CartItem Table (Mặt hàng trong giỏ)
CREATE TABLE IF NOT EXISTS cart_item (
    id SERIAL PRIMARY KEY,
    cart_id UUID NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
    article_id VARCHAR(20) NOT NULL REFERENCES product(article_id) ON DELETE CASCADE,
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity > 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_cart_item_cart_article UNIQUE (cart_id, article_id)
);

-- 11. Order Table (Đơn hàng)
CREATE TABLE IF NOT EXISTS "order" (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customer(id) ON DELETE RESTRICT,
    query_id UUID REFERENCES search_query(query_id) ON DELETE SET NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    total_amount_vnd INT NOT NULL CHECK (total_amount_vnd >= 0),
    shipping_address TEXT NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    payment_method VARCHAR(50) NOT NULL DEFAULT 'cod',
    payment_status VARCHAR(30) NOT NULL DEFAULT 'unpaid',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 12. OrderItem Table (Mặt hàng trong đơn)
CREATE TABLE IF NOT EXISTS order_item (
    id SERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES "order"(order_id) ON DELETE CASCADE,
    article_id VARCHAR(20) NOT NULL REFERENCES product(article_id) ON DELETE RESTRICT,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price_vnd INT NOT NULL CHECK (unit_price_vnd >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_order_item_order_article UNIQUE (order_id, article_id)
);

-- 13. Payment Table (Thanh toán)
CREATE TABLE IF NOT EXISTS payment (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES "order"(order_id) ON DELETE CASCADE,
    payment_method VARCHAR(50) NOT NULL DEFAULT 'cod',
    transaction_code VARCHAR(100),
    amount_vnd INT NOT NULL CHECK (amount_vnd >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 14. Shipment Table (Vận chuyển)
CREATE TABLE IF NOT EXISTS shipment (
    shipment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES "order"(order_id) ON DELETE CASCADE,
    tracking_number VARCHAR(100) UNIQUE,
    carrier VARCHAR(100) NOT NULL DEFAULT 'GiaoHangNhanh',
    shipping_address TEXT NOT NULL,
    recipient_name VARCHAR(150),
    recipient_phone VARCHAR(20),
    shipping_fee_vnd INT NOT NULL DEFAULT 0 CHECK (shipping_fee_vnd >= 0),
    status VARCHAR(30) NOT NULL DEFAULT 'preparing',
    estimated_delivery_date TIMESTAMP WITH TIME ZONE,
    shipped_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Compatibility Views for plural naming and legacy references
CREATE OR REPLACE VIEW user_profiles AS 
    SELECT id, email, full_name, phone_number, shipping_address, created_at, updated_at FROM customer;
CREATE OR REPLACE VIEW categories AS SELECT * FROM category;
CREATE OR REPLACE VIEW products AS SELECT * FROM product;
CREATE OR REPLACE VIEW orders AS SELECT * FROM "order";
CREATE OR REPLACE VIEW order_items AS SELECT * FROM order_item;
CREATE OR REPLACE VIEW carts AS SELECT * FROM cart;
CREATE OR REPLACE VIEW cart_items AS SELECT * FROM cart_item;
CREATE OR REPLACE VIEW payments AS SELECT * FROM payment;
CREATE OR REPLACE VIEW shipments AS SELECT * FROM shipment;

-- Indexes for Fast Query Filtering & Joins
CREATE INDEX IF NOT EXISTS idx_product_category_id ON product(category_id);
CREATE INDEX IF NOT EXISTS idx_product_color_code ON product(color_code);
CREATE INDEX IF NOT EXISTS idx_product_gender ON product(gender);
CREATE INDEX IF NOT EXISTS idx_product_price_vnd ON product(price_vnd);
CREATE INDEX IF NOT EXISTS idx_product_image_hash ON product(image_hash);
CREATE INDEX IF NOT EXISTS idx_customer_email ON customer(email);
CREATE INDEX IF NOT EXISTS idx_search_query_customer_id ON search_query(customer_id);
CREATE INDEX IF NOT EXISTS idx_search_result_query_id ON search_result(query_id);
CREATE INDEX IF NOT EXISTS idx_search_result_article_id ON search_result(article_id);
CREATE INDEX IF NOT EXISTS idx_order_customer_id ON "order"(customer_id);
CREATE INDEX IF NOT EXISTS idx_order_query_id ON "order"(query_id);
CREATE INDEX IF NOT EXISTS idx_cart_customer_id ON cart(customer_id);
CREATE INDEX IF NOT EXISTS idx_cart_query_id ON cart(query_id);

-- HNSW Cosine Index for Fast Visual Similarity Search directly on product
CREATE INDEX IF NOT EXISTS idx_product_image_hnsw 
ON product 
USING hnsw (image_embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);

-- HNSW Cosine Index for Fast Text Similarity Search directly on product
CREATE INDEX IF NOT EXISTS idx_product_text_hnsw 
ON product 
USING hnsw (text_embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
