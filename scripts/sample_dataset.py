"""Sample dataset script for H&M Fashion Dataset.

Performs stratified sampling to select a representative subset (default 5,000 items)
with balanced distribution across gender and major product categories.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sample_dataset")

# Mapping of H&M product_group_name / product_type_name to 6 high-level categories
CATEGORY_MAPPING: Dict[str, str] = {
    # Tops (30%)
    "Garment Upper body": "Tops",
    "Underwear": "Tops",
    # Bottoms (24%)
    "Garment Lower body": "Bottoms",
    # Dresses (12%)
    "Garment Full body": "Dresses",
    # Outerwear (12%)
    "Nightwear": "Outerwear",
    "Swimwear": "Outerwear",
    # Shoes (12%)
    "Shoes": "Shoes",
    # Bags & Accessories (10%)
    "Accessories": "Bags & Accessories",
    "Bags": "Bags & Accessories",
}

# Target distribution targets for Stratified Sampling (Total 5,000)
# 60% Ladieswear (3,000), 40% Menswear (2,000)
CATEGORY_RATIOS: Dict[str, float] = {
    "Tops": 0.30,
    "Bottoms": 0.24,
    "Dresses": 0.12,
    "Outerwear": 0.12,
    "Shoes": 0.12,
    "Bags & Accessories": 0.10,
}

GENDER_RATIOS: Dict[str, float] = {
    "Ladieswear": 0.60,
    "Menswear": 0.40,
}


def map_category_group(product_group: str) -> Optional[str]:
    """Maps H&M product_group_name into one of 6 target groups."""
    return CATEGORY_MAPPING.get(product_group, "Tops")


def generate_vnd_price(base_seed: int) -> int:
    """Generates realistic VND fashion retail prices between 199,000 and 1,990,000."""
    rng = np.random.default_rng(base_seed)
    price_steps = np.arange(199_000, 1_991_000, 50_000)
    return int(rng.choice(price_steps))


def get_image_path(images_dir: Path, article_id: str) -> Optional[Path]:
    """Finds image path for a given H&M article_id."""
    clean_id = str(article_id).zfill(10)
    folder_prefix = clean_id[:3]
    candidate = images_dir / folder_prefix / f"{clean_id}.jpg"
    if candidate.exists():
        return candidate
    candidate_flat = images_dir / f"{clean_id}.jpg"
    if candidate_flat.exists():
        return candidate_flat
    return None


def stratified_sample(
    df: pd.DataFrame,
    total_samples: int = 5000,
    random_state: int = 42,
) -> pd.DataFrame:
    """Performs stratified sampling across Gender and high-level Category."""
    if df.empty:
        raise ValueError("Input DataFrame is empty, cannot perform stratified sampling.")

    # Assign broad category
    df = df.copy()
    df["broad_category"] = df["product_group_name"].map(map_category_group)
    
    # Filter gender to Ladieswear & Menswear
    df = df[df["index_group_name"].isin(["Ladieswear", "Menswear"])]
    if df.empty:
        raise ValueError("No records found matching target gender categories (Ladieswear, Menswear).")

    samples: List[pd.DataFrame] = []

    for gender, g_ratio in GENDER_RATIOS.items():
        gender_quota = int(total_samples * g_ratio)
        df_gender = df[df["index_group_name"] == gender]

        for cat, c_ratio in CATEGORY_RATIOS.items():
            stratum_quota = int(gender_quota * c_ratio)
            df_stratum = df_gender[df_gender["broad_category"] == cat]
            
            if len(df_stratum) == 0:
                logger.warning("Empty stratum for %s - %s", gender, cat)
                continue
                
            n_take = min(len(df_stratum), stratum_quota)
            sampled_stratum = df_stratum.sample(n=n_take, random_state=random_state)
            samples.append(sampled_stratum)

    result_df = pd.concat(samples, ignore_index=True)
    
    # If slight deficit due to rounding/scarcity, fill randomly from remaining
    if len(result_df) < total_samples:
        remaining_indices = df.index.difference(result_df.index)
        needed = total_samples - len(result_df)
        if len(remaining_indices) > 0:
            fill_df = df.loc[remaining_indices].sample(
                n=min(needed, len(remaining_indices)),
                random_state=random_state
            )
            result_df = pd.concat([result_df, fill_df], ignore_index=True)

    logger.info("Stratified sampling completed: %d items selected.", len(result_df))
    return result_df


def create_mock_dataset(
    output_dir: Path,
    num_samples: int = 100,
) -> Tuple[pd.DataFrame, Path]:
    """Generates synthetic dataset for offline development and CI tests."""
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    genders = ["Ladieswear", "Menswear"]
    categories = [
        ("Garment Upper body", "T-shirt", "Tops"),
        ("Garment Lower body", "Trousers", "Bottoms"),
        ("Garment Full body", "Dress", "Dresses"),
        ("Nightwear", "Jacket", "Outerwear"),
        ("Shoes", "Sneakers", "Shoes"),
        ("Accessories", "Handbag", "Bags & Accessories"),
    ]
    colors = [
        ("09", "Black", ["đen", "black"]),
        ("10", "White", ["trắng", "white"]),
        ("06", "Light Grey", ["xám", "ghi", "grey"]),
        ("71", "Light Blue", ["xanh dương", "blue", "da trời"]),
        ("14", "Dark Blue", ["xanh đậm", "navy"]),
    ]

    records = []
    for i in range(num_samples):
        article_id = f"{i+1:010d}"
        cat_group, prod_type, broad_cat = categories[i % len(categories)]
        color_code, color_name, _ = colors[i % len(colors)]
        gender = genders[i % len(genders)]
        
        # Create a small valid test JPEG image (224x224 RGB)
        img_color = (
            (i * 37) % 256,
            (i * 73) % 256,
            (i * 109) % 256,
        )
        img = Image.new("RGB", (224, 224), color=img_color)
        img_file = images_dir / f"{article_id}.jpg"
        img.save(img_file, format="JPEG")

        records.append({
            "article_id": article_id,
            "product_code": f"P{i // 3:06d}",
            "prod_name": f"{gender} {color_name} {prod_type} Model {i}",
            "product_type_name": prod_type,
            "product_group_name": cat_group,
            "index_group_name": gender,
            "colour_group_code": color_code,
            "colour_group_name": color_name,
            "detail_desc": f"Casual {color_name.lower()} {prod_type.lower()} made from 100% cotton denim fabric.",
            "price_vnd": generate_vnd_price(i),
            "image_path": str(Path("images") / f"{article_id}.jpg"),
        })

    df = pd.DataFrame(records)
    csv_path = output_dir / "sample_articles.csv"
    df.to_csv(csv_path, index=False)
    logger.info("Mock dataset created with %d items at %s", len(df), csv_path)
    return df, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Stratified Sampling for H&M Dataset")
    parser.add_argument("--source-csv", type=str, help="Path to H&M articles.csv")
    parser.add_argument("--images-dir", type=str, help="Path to H&M images root directory")
    parser.add_argument("--output-dir", type=str, default="data", help="Output directory")
    parser.add_argument("--sample-size", type=int, default=5000, help="Number of items to sample")
    parser.add_argument("--mock", action="store_true", help="Generate mock data if raw data is unavailable")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.mock:
        logger.info("Generating mock dataset with %d items...", args.sample_size)
        create_mock_dataset(out_dir, num_samples=args.sample_size)
        return

    if not args.source_csv or not Path(args.source_csv).exists():
        logger.error("Source CSV '%s' not found. Use --mock flag to generate mock dataset.", args.source_csv)
        raise FileNotFoundError(f"Source CSV '{args.source_csv}' not found.")

    logger.info("Reading source articles from %s...", args.source_csv)
    df = pd.read_csv(args.source_csv, dtype={"article_id": str, "product_code": str})
    
    # Filter only available images if images_dir provided
    if args.images_dir:
        img_root = Path(args.images_dir)
        logger.info("Validating image availability in %s...", img_root)
        available_ids = set()
        for idx in df["article_id"]:
            if get_image_path(img_root, idx):
                available_ids.add(idx)
        df = df[df["article_id"].isin(available_ids)]
        logger.info("Retained %d articles with verified image files.", len(df))

    sampled = stratified_sample(df, total_samples=args.sample_size)

    # Add VND prices and relative image paths
    sampled["price_vnd"] = [generate_vnd_price(i) for i in range(len(sampled))]
    
    dest_img_dir = out_dir / "images"
    dest_img_dir.mkdir(parents=True, exist_ok=True)
    
    if args.images_dir:
        img_root = Path(args.images_dir)
        for _, row in sampled.iterrows():
            aid = row["article_id"]
            src_img = get_image_path(img_root, aid)
            if src_img:
                shutil.copy2(src_img, dest_img_dir / f"{aid}.jpg")
    
    sampled["image_path"] = sampled["article_id"].apply(lambda x: f"images/{x}.jpg")
    output_csv = out_dir / "sample_articles.csv"
    sampled.to_csv(output_csv, index=False)
    logger.info("Successfully exported sample to %s", output_csv)


if __name__ == "__main__":
    main()
