"""Database Migration Script for 14-Class UML Model.

Migrates legacy PostgreSQL schema to the new 14-class unified structure:
1. Merges vector embeddings into 'product' table.
2. Standardizes singular entity naming: customer, category, product, "order", order_item, cart, cart_item.
3. Provisions Table-per-Type search hierarchy: search_query, text_query, image_query, voice_query.
4. Provisions search_result table for query-product attribution.
5. Sets up backward-compatible views.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import psycopg

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migration_14_classes")


def get_connection(conn_str: Optional[str] = None) -> psycopg.Connection:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "search_engine")
    resolved_conn_str = conn_str or f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return psycopg.connect(resolved_conn_str, autocommit=False)


def run_migration(conn_str: Optional[str] = None) -> bool:
    """Executes safe, non-destructive migration on PostgreSQL."""
    try:
        with get_connection(conn_str) as conn:
            with conn.cursor() as cur:
                logger.info("Step 1: Enabling required extensions (uuid-ossp, vector)...")
                cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
                cur.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

                logger.info("Step 2: Checking existing tables...")
                cur.execute(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public';
                    """
                )
                existing_tables = {row[0] for row in cur.fetchall()}

                # Migrate user_profiles -> customer
                if "customer" not in existing_tables:
                    if "user_profiles" in existing_tables:
                        logger.info("Migrating user_profiles to customer...")
                        cur.execute("ALTER TABLE user_profiles RENAME TO customer;")
                        cur.execute("ALTER TABLE customer ADD COLUMN IF NOT EXISTS age INT;")
                    else:
                        logger.info("Creating customer table...")
                        cur.execute(
                            """
                            CREATE TABLE customer (
                                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                                full_name VARCHAR(150) NOT NULL,
                                email VARCHAR(255) NOT NULL UNIQUE,
                                age INT CHECK (age >= 0),
                                phone_number VARCHAR(20),
                                shipping_address TEXT,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                            );
                            """
                        )

                # Migrate categories -> category
                if "category" not in existing_tables:
                    if "categories" in existing_tables:
                        logger.info("Migrating categories to category...")
                        cur.execute("ALTER TABLE categories RENAME TO category;")
                    else:
                        logger.info("Creating category table...")
                        cur.execute(
                            """
                            CREATE TABLE category (
                                id SERIAL PRIMARY KEY,
                                group_name VARCHAR(100) NOT NULL,
                                sub_category VARCHAR(100) NOT NULL,
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                CONSTRAINT uq_category_group_sub UNIQUE (group_name, sub_category)
                            );
                            """
                        )

                # Migrate products -> product & merge embeddings
                if "product" not in existing_tables:
                    if "products" in existing_tables:
                        logger.info("Migrating products to product...")
                        cur.execute("ALTER TABLE products RENAME TO product;")
                    else:
                        logger.info("Creating product table...")
                        cur.execute(
                            """
                            CREATE TABLE product (
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
                            """
                        )

                # Ensure vector columns exist on product
                cur.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS image_embedding vector(768);")
                cur.execute("ALTER TABLE product ADD COLUMN IF NOT EXISTS text_embedding vector(768);")

                # If legacy product_embeddings table exists, backfill vectors into product
                if "product_embeddings" in existing_tables:
                    logger.info("Backfilling precomputed vectors from product_embeddings into product...")
                    cur.execute(
                        """
                        UPDATE product p
                        SET image_embedding = pe.image_embedding,
                            text_embedding = pe.text_embedding
                        FROM product_embeddings pe
                        WHERE p.article_id = pe.article_id
                          AND (p.image_embedding IS NULL OR p.text_embedding IS NULL);
                        """
                    )

                # Search TPT Hierarchy
                logger.info("Step 3: Creating SearchQuery hierarchy and SearchResult tables...")
                cur.execute(
                    """
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
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS text_query (
                        query_id UUID PRIMARY KEY REFERENCES search_query(query_id) ON DELETE CASCADE,
                        query_text TEXT NOT NULL
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS image_query (
                        query_id UUID PRIMARY KEY REFERENCES search_query(query_id) ON DELETE CASCADE,
                        image_reference VARCHAR(255) NOT NULL,
                        selected_region VARCHAR(100)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS voice_query (
                        query_id UUID PRIMARY KEY REFERENCES search_query(query_id) ON DELETE CASCADE,
                        transcribe_text TEXT NOT NULL,
                        audio_reference VARCHAR(255)
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS search_result (
                        id SERIAL PRIMARY KEY,
                        query_id UUID NOT NULL REFERENCES search_query(query_id) ON DELETE CASCADE,
                        article_id VARCHAR(20) NOT NULL REFERENCES product(article_id) ON DELETE CASCADE,
                        rank INT NOT NULL CHECK (rank >= 1),
                        score FLOAT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT uq_search_result_query_article UNIQUE (query_id, article_id)
                    );
                    """
                )

                # Commerce tables
                if "cart" not in existing_tables and "carts" in existing_tables:
                    cur.execute("ALTER TABLE carts RENAME TO cart;")
                if "cart_item" not in existing_tables and "cart_items" in existing_tables:
                    cur.execute("ALTER TABLE cart_items RENAME TO cart_item;")
                if "order" not in existing_tables and "orders" in existing_tables:
                    cur.execute('ALTER TABLE orders RENAME TO "order";')
                if "order_item" not in existing_tables and "order_items" in existing_tables:
                    cur.execute("ALTER TABLE order_items RENAME TO order_item;")

                cur.execute("ALTER TABLE cart ADD COLUMN IF NOT EXISTS query_id UUID REFERENCES search_query(query_id) ON DELETE SET NULL;")
                cur.execute('ALTER TABLE "order" ADD COLUMN IF NOT EXISTS query_id UUID REFERENCES search_query(query_id) ON DELETE SET NULL;')

                logger.info("Step 4: Creating HNSW indexes directly on product table...")
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_product_image_hnsw 
                    ON product 
                    USING hnsw (image_embedding vector_cosine_ops) 
                    WITH (m = 16, ef_construction = 64);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_product_text_hnsw 
                    ON product 
                    USING hnsw (text_embedding vector_cosine_ops) 
                    WITH (m = 16, ef_construction = 64);
                    """
                )

                logger.info("Step 5: Provisioning backward compatibility views...")
                views_sql = """
                CREATE OR REPLACE VIEW user_profiles AS SELECT id, email, full_name, phone_number, shipping_address, created_at, updated_at FROM customer;
                CREATE OR REPLACE VIEW categories AS SELECT * FROM category;
                CREATE OR REPLACE VIEW products AS SELECT * FROM product;
                CREATE OR REPLACE VIEW orders AS SELECT * FROM "order";
                CREATE OR REPLACE VIEW order_items AS SELECT * FROM order_item;
                CREATE OR REPLACE VIEW carts AS SELECT * FROM cart;
                CREATE OR REPLACE VIEW cart_items AS SELECT * FROM cart_item;
                """
                cur.execute(views_sql)

                conn.commit()
                logger.info("14-Class Database Migration completed successfully!")
                return True
    except Exception as e:
        logger.error("Migration failed or database unavailable: %s", e)
        return False


if __name__ == "__main__":
    run_migration()
