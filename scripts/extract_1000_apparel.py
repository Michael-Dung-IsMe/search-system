"""Script to extract 1,000 diverse apparel items from H&M dataset.

Filtering constraints:
- Strictly apparel (Garment Upper body, Lower body, Full body, Shoes).
- Excludes underwear, nightwear, swimwear, watches, socks/tights, and accessories.
- Balanced 50/50 gender distribution: 500 Ladieswear, 500 Menswear.
- Verifies image existence and copies 1,000 images to data/images/.
- Generates data/sample_articles.csv with realistic VND prices.
"""

import sys
from pathlib import Path
import shutil
import numpy as np
import pandas as pd
from tqdm import tqdm

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

SOURCE_CSV = Path(r"D:\datasets\h-and-m-personalized-fashion-recommendations\articles.csv")
SOURCE_IMAGES = Path(r"D:\datasets\h-and-m-personalized-fashion-recommendations\images")
DEST_DIR = Path(r"d:\PTIT\HỌC KỲ 7\PTTK-HTTT\search-system\data")
DEST_IMAGES = DEST_DIR / "images"

def generate_vnd_price(seed: int) -> int:
    rng = np.random.default_rng(seed)
    # Price steps from 199,000 VND to 1,990,000 VND
    steps = np.arange(199_000, 1_991_000, 50_000)
    return int(rng.choice(steps))

def main():
    print(f"Reading source articles from {SOURCE_CSV}...")
    df = pd.read_csv(
        SOURCE_CSV,
        dtype={
            "article_id": str,
            "product_code": str,
            "colour_group_code": str,
        }
    )
    print(f"Total raw articles: {len(df)}")

    # 1. Filter Adult Gender (Ladieswear and Menswear)
    df = df[df["index_group_name"].isin(["Ladieswear", "Menswear"])].copy()

    # 2. Focus on Garments & Shoes
    allowed_groups = ["Garment Upper body", "Garment Lower body", "Garment Full body", "Shoes"]
    df = df[df["product_group_name"].isin(allowed_groups)].copy()

    # 3. Explicit exclusion of underwear, nightwear, swimwear, watches, etc.
    exclude_keywords = [
        "underwear", "bra", "briefs", "boxer", "panties", "tights", "socks",
        "pyjama", "nightie", "swim", "bikini", "watch", "umbrella", "earring",
        "necklace", "ring", "sunglass", "headband"
    ]
    for kw in exclude_keywords:
        df = df[~df["product_type_name"].str.contains(kw, case=False, na=False)]
        df = df[~df["prod_name"].str.contains(kw, case=False, na=False)]

    print(f"Eligible apparel articles after exclusions: {len(df)}")

    # 4. Check image file existence
    def get_src_img(aid: str) -> Path | None:
        clean_id = str(aid).zfill(10)
        p = SOURCE_IMAGES / clean_id[:3] / f"{clean_id}.jpg"
        return p if p.exists() else None

    print("Verifying image files on disk...")
    df["src_img_path"] = df["article_id"].apply(get_src_img)
    df = df[df["src_img_path"].notna()].copy()
    print(f"Articles with verified images: {len(df)}")

    # 5. Stratified Quotas (500 Ladieswear, 500 Menswear = 1,000 total)
    # Ladieswear quotas: Upper: 180, Lower: 120, Full body (Dresses): 140, Shoes: 60
    ladies_quotas = {
        "Garment Upper body": 180,
        "Garment Lower body": 120,
        "Garment Full body": 140,
        "Shoes": 60,
    }
    # Menswear quotas: Upper: 300, Lower: 140, Shoes: 60
    men_quotas = {
        "Garment Upper body": 300,
        "Garment Lower body": 140,
        "Shoes": 60,
    }

    samples = []
    rng_seed = 42

    # Sample Ladieswear
    df_ladies = df[df["index_group_name"] == "Ladieswear"]
    for group_name, quota in ladies_quotas.items():
        subset = df_ladies[df_ladies["product_group_name"] == group_name]
        sampled_sub = subset.sample(n=min(len(subset), quota), random_state=rng_seed)
        samples.append(sampled_sub)

    # Sample Menswear
    df_men = df[df["index_group_name"] == "Menswear"]
    for group_name, quota in men_quotas.items():
        subset = df_men[df_men["product_group_name"] == group_name]
        sampled_sub = subset.sample(n=min(len(subset), quota), random_state=rng_seed)
        samples.append(sampled_sub)

    sampled_df = pd.concat(samples, ignore_index=True)
    print(f"Sampled total items: {len(sampled_df)}")
    print(sampled_df.groupby(["index_group_name", "product_group_name"]).size())

    # 6. Assign VND prices and image paths
    sampled_df["price_vnd"] = [generate_vnd_price(i + 100) for i in range(len(sampled_df))]
    sampled_df["image_path"] = sampled_df["article_id"].apply(lambda aid: f"images/{str(aid).zfill(10)}.jpg")

    # 7. Copy images to data/images/
    DEST_IMAGES.mkdir(parents=True, exist_ok=True)
    print(f"Copying {len(sampled_df)} images to {DEST_IMAGES}...")
    copied_count = 0
    for _, row in tqdm(sampled_df.iterrows(), total=len(sampled_df), desc="Copying images"):
        src_path: Path = row["src_img_path"]
        dest_path = DEST_IMAGES / f"{str(row['article_id']).zfill(10)}.jpg"
        shutil.copy2(src_path, dest_path)
        copied_count += 1

    print(f"Successfully copied {copied_count} images.")

    # 8. Save CSV (remove temporary helper column)
    sampled_df = sampled_df.drop(columns=["src_img_path"])
    out_csv = DEST_DIR / "sample_articles.csv"
    sampled_df.to_csv(out_csv, index=False)
    print(f"Saved {len(sampled_df)} items to {out_csv}")

if __name__ == "__main__":
    main()
