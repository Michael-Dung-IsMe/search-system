"""Unit and Contract-based Test Suite for Phase 1.

Verifies:
1. Stratified sampling logic (ratios, boundary conditions, empty dataset handling, deficit fill).
2. VND price generation (range checks, step checks).
3. EmbeddingExtractor (768-dim constraint, unit norm, batch consistency, model loading fallback).
4. Schema DDL statements and SQL foreign key / cascade contract definitions.
5. Database ingestion synchronization (categories map, colors synonyms, indexing pipeline).
6. CLI entrypoints for sample_dataset and index_products.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from scripts.sample_dataset import (
    CATEGORY_MAPPING,
    CATEGORY_RATIOS,
    GENDER_RATIOS,
    create_mock_dataset,
    generate_vnd_price,
    get_image_path,
    map_category_group,
    stratified_sample,
    main as sample_main,
)
from scripts.index_products import (
    COLOR_SYNONYMS,
    EmbeddingExtractor,
    calculate_image_hash,
    get_db_connection,
    get_or_compute_image_embedding,
    index_dataset,
    load_embeddings_from_file,
    save_embeddings_to_file,
    sync_categories,
    sync_colors,
    main as index_main,
)


class TestStratifiedSampling:
    """Tests data sampling constraints, distribution, and edge cases."""

    def test_map_category_group(self):
        assert map_category_group("Garment Upper body") == "Tops"
        assert map_category_group("Garment Lower body") == "Bottoms"
        assert map_category_group("Garment Full body") == "Dresses"
        assert map_category_group("Shoes") == "Shoes"
        assert map_category_group("Accessories") == "Bags & Accessories"
        # Unknown fallback defaults to Tops
        assert map_category_group("Unknown Mystery Group") == "Tops"

    def test_generate_vnd_price_bounds(self):
        for seed in range(50):
            price = generate_vnd_price(seed)
            assert 199_000 <= price <= 1_990_000
            assert (price - 199_000) % 50_000 == 0

    def test_stratified_sample_empty_dataframe(self):
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError, match="Input DataFrame is empty"):
            stratified_sample(empty_df, total_samples=100)

    def test_stratified_sample_no_matching_gender(self):
        df = pd.DataFrame({
            "product_group_name": ["Garment Upper body"],
            "index_group_name": ["Childrenswear"],
        })
        with pytest.raises(ValueError, match="No records found matching target gender"):
            stratified_sample(df, total_samples=10)

    def test_stratified_sample_distribution(self, tmp_path):
        mock_df, _ = create_mock_dataset(tmp_path, num_samples=300)
        sample_size = 100
        sampled = stratified_sample(mock_df, total_samples=sample_size, random_state=42)

        assert len(sampled) == sample_size
        gender_counts = sampled["index_group_name"].value_counts(normalize=True)
        # Ladieswear ~ 60%, Menswear ~ 40%
        assert gender_counts.get("Ladieswear", 0) >= 0.50
        assert gender_counts.get("Menswear", 0) >= 0.30

    def test_stratified_sample_deficit_fill(self, tmp_path):
        """Tests when certain strata have fewer items than quota and requires backfilling."""
        # Create an imbalanced dataset where only a few items exist for one group
        mock_df, _ = create_mock_dataset(tmp_path, num_samples=50)
        sampled = stratified_sample(mock_df, total_samples=40, random_state=42)
        assert len(sampled) == 40

    def test_create_mock_dataset(self, tmp_path):
        df, csv_path = create_mock_dataset(tmp_path, num_samples=20)
        assert csv_path.exists()
        assert len(df) == 20
        assert "article_id" in df.columns
        assert "price_vnd" in df.columns
        assert "detail_desc" in df.columns

        # Verify images were created
        for _, row in df.iterrows():
            img_file = tmp_path / row["image_path"]
            assert img_file.exists()

    def test_get_image_path(self, tmp_path):
        img_dir = tmp_path / "images"
        nested_dir = img_dir / "012"
        nested_dir.mkdir(parents=True)
        target_file = nested_dir / "0123456789.jpg"
        target_file.touch()

        found = get_image_path(img_dir, "123456789")
        assert found == target_file

        # Flat candidate check
        flat_file = img_dir / "0987654321.jpg"
        flat_file.touch()
        assert get_image_path(img_dir, "987654321") == flat_file

        # Non-existent ID returns None
        assert get_image_path(img_dir, "9999999999") is None

    def test_sample_dataset_main_cli_mock(self, tmp_path):
        test_args = ["sample_dataset.py", "--mock", "--sample-size", "15", "--output-dir", str(tmp_path)]
        with patch.object(sys, "argv", test_args):
            sample_main()
        assert (tmp_path / "sample_articles.csv").exists()

    def test_sample_dataset_main_cli_missing_source(self):
        test_args = ["sample_dataset.py", "--source-csv", "non_existent_file.csv"]
        with patch.object(sys, "argv", test_args):
            with pytest.raises(FileNotFoundError):
                sample_main()


class TestEmbeddingExtractor:
    """Tests 768-dim multimodal embedding properties and normalization."""

    def test_mock_embedding_shape_and_norm(self, tmp_path):
        extractor = EmbeddingExtractor(use_mock=True)
        dummy_img = tmp_path / "test.jpg"
        dummy_img.touch()

        vec = extractor.encode_image(dummy_img)
        assert isinstance(vec, np.ndarray)
        assert vec.shape == (768,)
        # Must be unit-normalized (L2 norm == 1.0)
        norm = np.linalg.norm(vec)
        assert pytest.approx(norm, rel=1e-4) == 1.0

    def test_mock_batch_embedding(self, tmp_path):
        extractor = EmbeddingExtractor(use_mock=True)
        img_paths = []
        for i in range(5):
            p = tmp_path / f"img_{i}.jpg"
            p.touch()
            img_paths.append(p)

        batch_vecs = extractor.encode_images_batch(img_paths)
        assert batch_vecs.shape == (5, 768)
        for vec in batch_vecs:
            assert pytest.approx(np.linalg.norm(vec), rel=1e-4) == 1.0

    @patch("torch.cuda.is_available", return_value=False)
    def test_extractor_device_fallback(self, mock_cuda):
        extractor = EmbeddingExtractor(use_mock=True)
        assert extractor.device == "cpu"


class TestDatabaseContractsAndSchema:
    """Tests SQL schema contracts, 3NF tables, and DB helpers."""

    def test_schema_sql_contract(self):
        schema_path = Path("backend/db/schema.sql")
        assert schema_path.exists()
        content = schema_path.read_text(encoding="utf-8")

        # Verify extension declarations
        assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in content
        assert 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"' in content

        # Verify all 14 tables exist in DDL
        tables = [
            "customer",
            "category",
            "product",
            "search_query",
            "text_query",
            "image_query",
            "voice_query",
            "search_result",
            "cart",
            "cart_item",
            '"order"',
            "order_item",
            "payment",
            "shipment",
        ]
        for tbl in tables:
            assert f"CREATE TABLE IF NOT EXISTS {tbl}" in content

        # Verify 768-dim vector column
        assert "image_embedding vector(768)" in content
        assert "text_embedding vector(768)" in content

        # Verify image_hash column and index exist
        assert "image_hash VARCHAR(64)" in content
        assert "idx_product_image_hash" in content

        # Verify HNSW index with cosine distance for image and text embeddings directly on product
        assert "USING hnsw (image_embedding vector_cosine_ops)" in content
        assert "USING hnsw (text_embedding vector_cosine_ops)" in content
        assert "ON product" in content

        # Verify foreign keys with ON DELETE CASCADE
        assert "REFERENCES search_query(query_id) ON DELETE CASCADE" in content

    def test_get_db_connection(self):
        with patch("psycopg.connect") as mock_connect:
            get_db_connection("postgresql://test:test@localhost:5432/test")
            mock_connect.assert_called_with("postgresql://test:test@localhost:5432/test")

        with patch("psycopg.connect") as mock_connect, patch.dict(os.environ, {"POSTGRES_PORT": "5433"}):
            get_db_connection()
            assert mock_connect.called

    def test_sync_categories_mock_db(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [(1,), (2,)]

        df = pd.DataFrame({
            "product_group_name": ["Tops", "Bottoms"],
            "product_type_name": ["T-shirt", "Trousers"],
        })

        cat_map = sync_categories(mock_conn, df)
        assert len(cat_map) == 2
        assert cat_map[("Tops", "T-shirt")] == 1
        assert cat_map[("Bottoms", "Trousers")] == 2
        assert mock_cur.execute.call_count == 2
        assert mock_conn.commit.called

    def test_sync_colors_mock_db(self):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur

        df = pd.DataFrame({
            "colour_group_code": ["09", "10"],
            "colour_group_name": ["Black", "White"],
        })

        sync_colors(mock_conn, df)
        assert mock_cur.execute.call_count == 2
        assert mock_conn.commit.called

    def test_index_dataset_pipeline(self, tmp_path):
        """Tests the full indexing pipeline with mock database and mock embeddings."""
        df, csv_path = create_mock_dataset(tmp_path, num_samples=6)
        extractor = EmbeddingExtractor(use_mock=True)

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        # For sync_categories, return consecutive ids
        mock_cur.fetchone.side_effect = [(1,), (2,), (3,), (4,), (5,), (6,)]

        with patch("scripts.index_products.get_db_connection", return_value=mock_conn):
            total_indexed = index_dataset(
                csv_path=csv_path,
                images_root=tmp_path / "images",
                extractor=extractor,
                batch_size=2,
                conn_str="mock_connection_string",
            )
            assert total_indexed == 6
            assert mock_conn.commit.called

    def test_index_dataset_skip_missing_image(self, tmp_path):
        """Ensures articles without valid image files are gracefully skipped without failure."""
        df, csv_path = create_mock_dataset(tmp_path, num_samples=4)
        # Delete one image
        missing_img = tmp_path / df.iloc[0]["image_path"]
        if missing_img.exists():
            missing_img.unlink()

        extractor = EmbeddingExtractor(use_mock=True)
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [(1,), (2,), (3,), (4,)]

        with patch("scripts.index_products.get_db_connection", return_value=mock_conn):
            total_indexed = index_dataset(
                csv_path=csv_path,
                images_root=tmp_path / "images",
                extractor=extractor,
                batch_size=2,
            )
            assert total_indexed == 3

    def test_index_products_main_cli(self, tmp_path):
        df, csv_path = create_mock_dataset(tmp_path, num_samples=3)
        test_args = [
            "index_products.py",
            "--csv", str(csv_path),
            "--images-dir", str(tmp_path / "images"),
            "--batch-size", "2",
            "--mock-embedding",
        ]
        with patch.object(sys, "argv", test_args), patch("scripts.index_products.index_dataset", return_value=3) as mock_idx:
            index_main()
            assert mock_idx.called

    def test_save_and_load_embeddings_file(self, tmp_path):
        """Tests saving embeddings to .npz file and loading back."""
        file_path = tmp_path / "embeddings.npz"
        ids = ["0123456789", "0987654321"]
        vectors = np.random.randn(2, 768).astype(np.float32)

        save_embeddings_to_file(file_path, ids, vectors)
        assert file_path.exists()

        loaded_map = load_embeddings_from_file(file_path)
        assert len(loaded_map) == 2
        assert "0123456789" in loaded_map
        assert "0987654321" in loaded_map
        np.testing.assert_allclose(loaded_map["0123456789"], vectors[0], rtol=1e-5)
        np.testing.assert_allclose(loaded_map["0987654321"], vectors[1], rtol=1e-5)

    def test_load_embeddings_missing_file_raises(self, tmp_path):
        """Ensures loading from a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Embeddings file not found"):
            load_embeddings_from_file(tmp_path / "non_existent.npz")

    def test_index_dataset_with_save_and_load_embeddings(self, tmp_path):
        """Tests that index_dataset saves embeddings and reuses them on load."""
        df, csv_path = create_mock_dataset(tmp_path, num_samples=4)
        extractor = EmbeddingExtractor(use_mock=True)
        save_file = tmp_path / "out_embeddings.npz"

        mock_conn = MagicMock()
        mock_conn.__enter__.return_value = mock_conn
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        mock_cur.fetchone.side_effect = [(1,), (2,), (3,), (4,)]

        with patch("scripts.index_products.get_db_connection", return_value=mock_conn):
            total_1 = index_dataset(
                csv_path=csv_path,
                images_root=tmp_path / "images",
                extractor=extractor,
                batch_size=2,
                save_embeddings_path=save_file,
            )
            assert total_1 == 4
            assert save_file.exists()

        # Now test indexing with load_embeddings_path (mock encoder should not be called)
        mock_cur.fetchone.side_effect = [(1,), (2,), (3,), (4,)]
        with patch("scripts.index_products.get_db_connection", return_value=mock_conn):
            with patch.object(extractor, "encode_images_batch") as mock_encode:
                total_2 = index_dataset(
                    csv_path=csv_path,
                    images_root=tmp_path / "images",
                    extractor=extractor,
                    batch_size=2,
                    load_embeddings_path=save_file,
                )
                assert total_2 == 4
                mock_encode.assert_not_called()

    def test_calculate_image_hash_variations(self, tmp_path):
        """Tests image hashing for Path, bytes, PIL Image, and invalid types."""
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (30, 30), color="blue")
        img_path = tmp_path / "test_hash.png"
        img.save(img_path)

        hash_path = calculate_image_hash(img_path)
        hash_bytes = calculate_image_hash(img_path.read_bytes())
        assert hash_path == hash_bytes
        assert len(hash_path) == 64

        # PIL Image directly
        hash_pil = calculate_image_hash(img)
        assert len(hash_pil) == 64

        # Invalid type
        with pytest.raises(TypeError, match="Unsupported image input type"):
            calculate_image_hash(12345)

    def test_encode_image_input_types(self, tmp_path):
        """Ensures encode_image works across Path, bytes, and PIL Image instances."""
        from PIL import Image as PILImage
        extractor = EmbeddingExtractor(use_mock=True)
        img = PILImage.new("RGB", (20, 20), color="red")
        img_path = tmp_path / "test_encode.png"
        img.save(img_path)

        vec_path = extractor.encode_image(img_path)
        vec_bytes = extractor.encode_image(img_path.read_bytes())
        vec_pil = extractor.encode_image(img)

        assert vec_path.shape == (768,)
        assert vec_bytes.shape == (768,)
        assert vec_pil.shape == (768,)

    def test_encode_text_and_batch(self):
        """Ensures encode_text and encode_texts_batch work with mock extractor."""
        extractor = EmbeddingExtractor(use_mock=True)
        t_vec = extractor.encode_text("Áo sơ mi trắng công sở")
        assert t_vec.shape == (768,)
        assert np.isclose(np.linalg.norm(t_vec), 1.0, atol=1e-4)

        # Empty text fallback
        empty_vec = extractor.encode_text("")
        assert empty_vec.shape == (768,)
        assert empty_vec[0] == 1.0

        # Batch encode
        batch_vecs = extractor.encode_texts_batch(["Váy đầm đen", "Quần jean xanh"])
        assert batch_vecs.shape == (2, 768)

    def test_get_or_compute_image_embedding_catalog_hit(self, tmp_path):
        """Tests Cache HIT from catalog products table."""
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (20, 20), color="green")
        extractor = EmbeddingExtractor(use_mock=True)

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        dummy_vec = [0.1] * 768
        mock_cur.fetchone.return_value = (dummy_vec,)

        vec, is_hit = get_or_compute_image_embedding(img, extractor, conn=mock_conn)
        assert is_hit is True
        assert vec.shape == (768,)
        assert np.isclose(vec[0], 0.1)

    def test_get_or_compute_image_embedding_uploaded_cache_hit(self, tmp_path):
        """Tests Cache HIT from uploaded_image_cache table."""
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (20, 20), color="yellow")
        extractor = EmbeddingExtractor(use_mock=True)

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        # First query (catalog) returns None, second (cache) returns vector
        dummy_vec = [0.2] * 768
        mock_cur.fetchone.side_effect = [None, (dummy_vec,)]

        vec, is_hit = get_or_compute_image_embedding(img, extractor, conn=mock_conn)
        assert is_hit is True
        assert vec.shape == (768,)
        assert np.isclose(vec[0], 0.2)

    def test_get_or_compute_image_embedding_cache_miss_computes_and_inserts(self, tmp_path):
        """Tests Cache MISS computes new vector and saves into uploaded_image_cache."""
        from PIL import Image as PILImage
        img = PILImage.new("RGB", (20, 20), color="white")
        extractor = EmbeddingExtractor(use_mock=True)

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        # Both catalog and cache lookups return None
        mock_cur.fetchone.side_effect = [None, None]

        vec, is_hit = get_or_compute_image_embedding(img, extractor, conn=mock_conn)
        assert is_hit is False
        assert vec.shape == (768,)
        # Verify inserted into uploaded_image_cache and committed
        assert mock_cur.execute.call_count == 3
        assert mock_conn.commit.called
