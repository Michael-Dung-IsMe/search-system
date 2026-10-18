"""Index products and embeddings into PostgreSQL + pgvector.

Extracts normalized 768-dimensional visual embeddings using Marqo/marqo-fashionSigLIP
and populates the 3NF schema tables: categories, colors, products, product_embeddings.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from dotenv import load_dotenv
import numpy as np
import pandas as pd
import psycopg
from PIL import Image
import torch
from tqdm import tqdm

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("index_products")


def calculate_image_hash(image_input: Union[Path, str, bytes, Image.Image]) -> str:
    """Calculates SHA-256 hash of an image from file path, raw bytes, or PIL Image."""
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        return hashlib.sha256(p.read_bytes()).hexdigest()
    elif isinstance(image_input, bytes):
        return hashlib.sha256(image_input).hexdigest()
    elif isinstance(image_input, Image.Image):
        buf = io.BytesIO()
        image_input.save(buf, format="PNG")
        return hashlib.sha256(buf.getvalue()).hexdigest()
    raise TypeError(f"Unsupported image input type: {type(image_input)}")

# Initial dictionary of common H&M color synonyms (Vietnamese & English)
COLOR_SYNONYMS: Dict[str, List[str]] = {
    "09": ["đen", "black", "huyền", "tối"],
    "10": ["trắng", "white", "bạch", "sáng"],
    "06": ["xám", "ghi", "grey", "gray"],
    "71": ["xanh dương nhạt", "light blue", "da trời"],
    "14": ["xanh navy", "xanh đen", "dark blue", "navy"],
    "12": ["xanh lam", "blue", "xanh dương"],
    "08": ["xám đậm", "dark grey", "than"],
    "02": ["be", "beige", "kem"],
    "01": ["trắng sữa", "off white", "kem sáng"],
    "42": ["đỏ", "red", "đỏ tươi"],
    "43": ["đỏ đô", "dark red", "đỏ rượu", "maroon"],
    "51": ["hồng", "pink"],
    "61": ["tím", "purple", "violet"],
    "73": ["xanh lá", "green", "lục"],
    "81": ["vàng", "yellow"],
    "31": ["cam", "orange"],
    "21": ["nâu", "brown", "nâu đất"],
}


def get_db_connection(conn_str: Optional[str] = None) -> psycopg.Connection:
    """Creates a psycopg connection using environment variables or connection string."""
    if conn_str:
        return psycopg.connect(conn_str)
    
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    dbname = os.getenv("POSTGRES_DB", "fashion_search")

    return psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
    )


class EmbeddingExtractor:
    """Extracts 768-dim multimodal embeddings using OpenCLIP for images and OpenAI text-embedding-3-small for texts."""

    def __init__(
        self,
        model_name: str = "hf-hub:Marqo/marqo-fashionSigLIP",
        text_model_name: str = "text-embedding-3-small",
        use_mock: bool = False,
    ):
        self.use_mock = use_mock
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.text_model_name = text_model_name
        self.text_dimensions = 768
        self._openai_client = None

        if self.openai_key and not use_mock:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_key)
                logger.info("OpenAI client initialized for text embeddings (%s, 768-dim).", self.text_model_name)
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client (%s). Will fallback to SigLIP.", e)

        if not use_mock:
            logger.info("Loading OpenCLIP model '%s' on %s...", model_name, self.device)
            import open_clip

            self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                model_name,
                device=self.device,
            )
            self.tokenizer = open_clip.get_tokenizer(model_name)
            self.model.eval()
            logger.info("Model loaded successfully.")
        else:
            logger.info("Running EmbeddingExtractor in MOCK mode (768-D pseudo vectors).")

    def encode_image(self, image_input: Union[Path, str, bytes, Image.Image]) -> np.ndarray:
        """Encodes an image to a unit-normalized 768-dim vector."""
        if self.use_mock:
            seed = sum(ord(c) for c in str(image_input)[:100]) % 100000
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(768).astype(np.float32)
            norm = np.linalg.norm(vec)
            return vec / (norm + 1e-8)

        if isinstance(image_input, (str, Path)):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            image = image_input.convert("RGB")
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        tensor = self.preprocess(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy().squeeze().astype(np.float32)

    def encode_images_batch(self, image_paths: List[Path]) -> np.ndarray:
        """Batch-encodes multiple images for high-throughput GPU inference."""
        if self.use_mock:
            return np.vstack([self.encode_image(p) for p in image_paths])

        tensors = []
        for p in image_paths:
            img = Image.open(p).convert("RGB")
            tensors.append(self.preprocess(img))

        batch = torch.stack(tensors).to(self.device)
        with torch.no_grad():
            features = self.model.encode_image(batch)
            features = features / features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy().astype(np.float32)

    def encode_text(self, text: str) -> np.ndarray:
        """Encodes text description into a unit-normalized 768-dim vector using OpenAI (or SigLIP fallback)."""
        if not text:
            vec = np.zeros(768, dtype=np.float32)
            vec[0] = 1.0
            return vec

        if self.use_mock:
            seed = sum(ord(c) for c in str(text)[:100]) % 100000
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(768).astype(np.float32)
            norm = np.linalg.norm(vec)
            return vec / (norm + 1e-8)

        # 1. Primary: OpenAI text-embedding-3-small
        if self._openai_client:
            try:
                resp = self._openai_client.embeddings.create(
                    input=text,
                    model=self.text_model_name,
                    dimensions=self.text_dimensions,
                )
                vec = np.array(resp.data[0].embedding, dtype=np.float32)
                return vec / (np.linalg.norm(vec) + 1e-8)
            except Exception as e:
                logger.warning("OpenAI text embedding failed (%s), falling back to SigLIP.", e)

        # 2. Fallback: Local SigLIP
        if self.model and self.tokenizer:
            with torch.no_grad():
                tokens = self.tokenizer([text]).to(self.device)
                features = self.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                return features.cpu().numpy().squeeze().astype(np.float32)

        seed = sum(ord(c) for c in str(text)[:100]) % 100000
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(768).astype(np.float32)
        return vec / (np.linalg.norm(vec) + 1e-8)

    def encode_texts_batch(self, texts: List[str], batch_size: int = 250) -> np.ndarray:
        """Batch-encodes multiple text strings using OpenAI (or SigLIP fallback)."""
        if not texts:
            return np.empty((0, 768), dtype=np.float32)

        if self.use_mock:
            return np.vstack([self.encode_text(t) for t in texts])

        # 1. Primary: OpenAI batch embedding
        if self._openai_client:
            try:
                all_vectors = []
                for i in range(0, len(texts), batch_size):
                    chunk = texts[i : i + batch_size]
                    resp = self._openai_client.embeddings.create(
                        input=chunk,
                        model=self.text_model_name,
                        dimensions=self.text_dimensions,
                    )
                    all_vectors.extend([np.array(item.embedding, dtype=np.float32) for item in resp.data])
                mat = np.vstack(all_vectors)
                norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
                return mat / norms
            except Exception as e:
                logger.warning("OpenAI batch text embedding failed (%s), falling back to SigLIP.", e)

        # 2. Fallback: SigLIP batch embedding
        if self.model and self.tokenizer:
            with torch.no_grad():
                tokens = self.tokenizer(texts).to(self.device)
                features = self.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                return features.cpu().numpy().astype(np.float32)

        return np.vstack([self.encode_text(t) for t in texts])


def sync_categories(conn: psycopg.Connection, df: pd.DataFrame) -> Dict[Tuple[str, str], int]:
    """Populates categories table and returns a mapping from (group, sub) -> category_id."""
    unique_cats = df[["product_group_name", "product_type_name"]].drop_duplicates()
    cat_map: Dict[Tuple[str, str], int] = {}

    with conn.cursor() as cur:
        for _, row in unique_cats.iterrows():
            group = str(row["product_group_name"])
            sub = str(row["product_type_name"])
            cur.execute(
                """
                INSERT INTO category (group_name, sub_category)
                VALUES (%s, %s)
                ON CONFLICT (group_name, sub_category) DO UPDATE
                SET sub_category = EXCLUDED.sub_category
                RETURNING id;
                """,
                (group, sub),
            )
            cat_id = cur.fetchone()[0]
            cat_map[(group, sub)] = cat_id

    conn.commit()
    logger.info("Synchronized %d categories in database.", len(cat_map))
    return cat_map


def sync_colors(conn: psycopg.Connection, df: pd.DataFrame) -> None:
    """Populates colors table with names and multi-lingual synonyms."""
    unique_colors = df[["colour_group_code", "colour_group_name"]].drop_duplicates()

    try:
        with conn.cursor() as cur:
            for _, row in unique_colors.iterrows():
                code = str(row["colour_group_code"]).zfill(2)
                name = str(row["colour_group_name"])
                synonyms = COLOR_SYNONYMS.get(code, [name.lower()])
                cur.execute(
                    """
                    INSERT INTO colors (code, name, synonyms)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (code) DO UPDATE
                    SET name = EXCLUDED.name,
                        synonyms = EXCLUDED.synonyms;
                    """,
                    (code, name, synonyms),
                )
        conn.commit()
        logger.info("Synchronized colors in database.")
    except Exception as e:
        logger.info("Colors table not present or optional (%s), skipping DB color sync.", e)


def save_embeddings_to_file(
    file_path: Path,
    article_ids: List[str],
    embeddings: np.ndarray,
    text_embeddings: Optional[np.ndarray] = None,
) -> None:
    """Saves computed image and text embeddings and article IDs into a compressed .npz file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    save_dict = {
        "article_ids": np.array(article_ids, dtype=object),
        "embeddings": embeddings.astype(np.float32),
        "image_embeddings": embeddings.astype(np.float32),
    }
    if text_embeddings is not None:
        save_dict["text_embeddings"] = text_embeddings.astype(np.float32)

    np.savez_compressed(
        file_path,
        **save_dict,
    )
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    logger.info("Saved %d embeddings to %s (file size: %.2f MB).", len(article_ids), file_path, file_size_mb)


def load_embeddings_from_file(file_path: Path) -> Dict[str, np.ndarray]:
    """Loads precomputed embeddings from a .npz file into a dictionary mapping article_id -> vector."""
    if not file_path.exists():
        raise FileNotFoundError(f"Embeddings file not found: {file_path}")
    data = np.load(file_path, allow_pickle=True)
    article_ids = [str(aid).zfill(10) for aid in data["article_ids"]]
    key = "image_embeddings" if "image_embeddings" in data else "embeddings"
    embeddings = data[key].astype(np.float32)
    logger.info("Loaded %d precomputed embeddings from %s.", len(article_ids), file_path)
    return dict(zip(article_ids, embeddings))


def get_or_compute_image_embedding(
    image_input: Union[Path, str, bytes, Image.Image],
    extractor: EmbeddingExtractor,
    conn: Optional[psycopg.Connection] = None,
    conn_str: Optional[str] = None,
) -> Tuple[np.ndarray, bool]:
    """Retrieves precomputed embedding for an image if already indexed, or computes and caches it.
    
    Checks in sequence:
    1. Catalog products table (products.image_hash -> product_embeddings.image_embedding)
    2. Uploaded image cache table (uploaded_image_cache.embedding)
    3. Fallback: computes new embedding via extractor and caches into uploaded_image_cache.

    Returns:
        Tuple[np.ndarray, bool]: (embedding_vector_768d, is_precomputed_hit)
    """
    img_hash = calculate_image_hash(image_input)

    should_close_conn = False
    if conn is None:
        conn = get_db_connection(conn_str)
        should_close_conn = True

    try:
        with conn.cursor() as cur:
            # 1. Check if image matches an existing catalog product
            cur.execute(
                """
                SELECT p.image_embedding
                FROM product p
                WHERE p.image_hash = %s AND p.image_embedding IS NOT NULL
                LIMIT 1;
                """,
                (img_hash,),
            )
            row = cur.fetchone()
            if row is not None and row[0] is not None:
                vec = np.array(row[0], dtype=np.float32)
                logger.info("Cache HIT: Reusing precomputed catalog embedding for image hash %s...", img_hash[:12])
                return vec, True

            # 2. Check uploaded_image_cache
            cur.execute(
                "SELECT embedding FROM uploaded_image_cache WHERE image_hash = %s LIMIT 1;",
                (img_hash,),
            )
            row = cur.fetchone()
            if row is not None:
                vec = np.array(row[0], dtype=np.float32)
                logger.info("Cache HIT: Reusing uploaded cache embedding for image hash %s...", img_hash[:12])
                return vec, True

            # 3. Cache MISS: Compute embedding and save to uploaded_image_cache
            logger.info("Cache MISS: Computing new visual embedding for image hash %s...", img_hash[:12])
            vec = extractor.encode_image(image_input)

            cur.execute(
                """
                INSERT INTO uploaded_image_cache (image_hash, embedding)
                VALUES (%s, %s)
                ON CONFLICT (image_hash) DO NOTHING;
                """,
                (img_hash, vec.tolist()),
            )
            conn.commit()
            return vec, False
    finally:
        if should_close_conn:
            conn.close()



def index_dataset(
    csv_path: Path,
    images_root: Path,
    extractor: EmbeddingExtractor,
    batch_size: int = 32,
    conn_str: Optional[str] = None,
    save_embeddings_path: Optional[Path] = None,
    load_embeddings_path: Optional[Path] = None,
) -> int:
    """Reads sampled articles, calculates embeddings, and indexes into PostgreSQL."""
    df = pd.read_csv(csv_path, dtype={"article_id": str, "colour_group_code": str})
    logger.info("Loaded %d articles from %s.", len(df), csv_path)

    precomputed_vecs: Dict[str, np.ndarray] = {}
    if load_embeddings_path:
        precomputed_vecs = load_embeddings_from_file(load_embeddings_path)

    with get_db_connection(conn_str) as conn:
        cat_map = sync_categories(conn, df)
        sync_colors(conn, df)

        total_indexed = 0
        all_indexed_ids: List[str] = []
        all_indexed_vectors: List[np.ndarray] = []
        all_indexed_text_vectors: List[np.ndarray] = []

        for i in tqdm(range(0, len(df), batch_size), desc="Indexing products"):
            batch_df = df.iloc[i : i + batch_size]
            batch_img_paths = []
            valid_rows = []

            for _, row in batch_df.iterrows():
                rel_path = str(row.get("image_path", ""))
                clean_rel = rel_path.replace("\\", "/").lstrip("/")
                
                # Check candidate locations
                candidate_paths = [
                    images_root / clean_rel,
                    images_root / Path(clean_rel).name,
                ]
                if clean_rel.startswith("images/"):
                    candidate_paths.append(images_root / clean_rel[len("images/"):])

                img_path = None
                for cand in candidate_paths:
                    if cand.exists():
                        img_path = cand
                        break

                if not img_path or not img_path.exists():
                    logger.warning("Image missing for article %s, skipping.", row["article_id"])
                    continue

                batch_img_paths.append(img_path)
                valid_rows.append(row)

            if not valid_rows:
                continue

            # Determine which items are cached vs require model inference
            cached_results: Dict[int, np.ndarray] = {}
            to_encode_indices: List[int] = []
            to_encode_paths: List[Path] = []

            for idx, (row, img_path) in enumerate(zip(valid_rows, batch_img_paths)):
                aid = str(row["article_id"]).zfill(10)
                if aid in precomputed_vecs:
                    cached_results[idx] = precomputed_vecs[aid]
                else:
                    to_encode_indices.append(idx)
                    to_encode_paths.append(img_path)

            if to_encode_paths:
                new_vectors = extractor.encode_images_batch(to_encode_paths)
                for idx, vec in zip(to_encode_indices, new_vectors):
                    cached_results[idx] = vec

            vectors = [cached_results[idx] for idx in range(len(valid_rows))]
            text_descriptions = [
                f"{row.get('prod_name', '')} {row.get('product_type_name', '')} {row.get('product_group_name', '')}. {row.get('detail_desc', '')}".strip()
                for row in valid_rows
            ]
            text_vectors = extractor.encode_texts_batch(text_descriptions)

            with conn.cursor() as cur:
                for idx, (row, vec) in enumerate(zip(valid_rows, vectors)):
                    article_id = str(row["article_id"]).zfill(10)
                    prod_code = str(row.get("product_code", f"P{article_id}"))
                    prod_name = str(row.get("prod_name", "Fashion Item"))
                    group = str(row["product_group_name"])
                    sub = str(row["product_type_name"])
                    cat_id = cat_map[(group, sub)]
                    color_code = str(row["colour_group_code"]).zfill(2)
                    gender = str(row.get("index_group_name", "Ladieswear"))
                    price = int(row.get("price_vnd", 499000))
                    desc = str(row.get("detail_desc", ""))
                    img_rel = str(row.get("image_path", f"images/{article_id}.jpg"))
                    img_hash = calculate_image_hash(batch_img_paths[idx])
                    text_vec = text_vectors[idx]

                    # Insert product metadata and vectors directly into product table
                    cur.execute(
                        """
                        INSERT INTO product (
                            article_id, product_code, prod_name, category_id,
                            color_code, gender, price_vnd, detail_desc, image_path, image_hash,
                            image_embedding, text_embedding
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (article_id) DO UPDATE SET
                            prod_name = EXCLUDED.prod_name,
                            price_vnd = EXCLUDED.price_vnd,
                            detail_desc = EXCLUDED.detail_desc,
                            image_hash = EXCLUDED.image_hash,
                            image_embedding = EXCLUDED.image_embedding,
                            text_embedding = EXCLUDED.text_embedding;
                        """,
                        (article_id, prod_code, prod_name, cat_id, color_code, gender, price, desc, img_rel, img_hash, vec.tolist(), text_vec.tolist()),
                    )
                    total_indexed += 1
                    all_indexed_ids.append(article_id)
                    all_indexed_vectors.append(vec)
                    all_indexed_text_vectors.append(text_vec)

                conn.commit()

        if save_embeddings_path and all_indexed_vectors:
            save_embeddings_to_file(
                save_embeddings_path,
                all_indexed_ids,
                np.vstack(all_indexed_vectors),
                np.vstack(all_indexed_text_vectors) if all_indexed_text_vectors else None,
            )

        logger.info("Successfully indexed %d products into PostgreSQL.", total_indexed)
        return total_indexed


def main() -> None:
    parser = argparse.ArgumentParser(description="Index H&M fashion items into pgvector")
    parser.add_argument("--csv", type=str, default="data/sample_articles.csv", help="Sampled CSV path")
    parser.add_argument("--images-dir", type=str, default="data/images", help="Images directory")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size for embedding generation")
    parser.add_argument("--mock-embedding", action="store_true", help="Use mock embedding for quick local testing")
    parser.add_argument("--save-embeddings", type=str, default="data/embeddings.npz", help="Path to save precomputed embeddings (.npz)")
    parser.add_argument("--no-save-embeddings", action="store_true", help="Disable saving embeddings to file")
    parser.add_argument("--load-embeddings", type=str, default=None, help="Path to load precomputed embeddings (.npz) instead of re-encoding")
    args = parser.parse_args()

    save_path = None if args.no_save_embeddings else Path(args.save_embeddings)
    load_path = Path(args.load_embeddings) if args.load_embeddings else None

    extractor = EmbeddingExtractor(use_mock=args.mock_embedding)
    index_dataset(
        csv_path=Path(args.csv),
        images_root=Path(args.images_dir),
        extractor=extractor,
        batch_size=args.batch_size,
        save_embeddings_path=save_path,
        load_embeddings_path=load_path,
    )


if __name__ == "__main__":
    main()
