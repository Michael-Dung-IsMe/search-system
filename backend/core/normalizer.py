"""Entity and Dialect Normalizer for Fashion Search Engine.

Maps natural language entities (colors, categories, materials, prices)
from Vietnamese and English queries to standardized database keys.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Pre-compiled phonetic and dialect correction rules (North/Central/South dialects)
DIALECT_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(dày|dầy|giầy)\s+(da|thể\s+thao|sneaker|lười|cao\s+gót)\b", re.IGNORECASE), r"giày \2"),
    (re.compile(r"\bdày\b", re.IGNORECASE), "giày"),
    (re.compile(r"\bbận\b", re.IGNORECASE), "mặc"),
    (re.compile(r"\b(chiệu|chẹo)\b", re.IGNORECASE), "triệu"),
    (re.compile(r"\bquờn\b", re.IGNORECASE), "quần"),
    (re.compile(r"\bkiếm\b", re.IGNORECASE), "tìm"),
    (re.compile(r"\bxêm\b", re.IGNORECASE), "xem"),
    (re.compile(r"\blấy\s+cái\s+này\b", re.IGNORECASE), "giống cái này"),
]

# Canonical color taxonomy used by the H&M dataset bundled with this project.
# Product rows store only these codes, so filtering must resolve names to codes first.
COLOR_NAME_BY_CODE: Dict[str, str] = {
    "-1": "Unknown",
    "01": "Other",
    "03": "Silver",
    "04": "Bronze/Copper",
    "06": "Light Grey",
    "07": "Grey",
    "08": "Dark Grey",
    "09": "Black",
    "10": "White",
    "11": "Off White",
    "12": "Light Beige",
    "13": "Beige",
    "14": "Dark Beige",
    "15": "Greyish Beige",
    "17": "Yellowish Brown",
    "19": "Greenish Khaki",
    "21": "Light Yellow",
    "22": "Yellow",
    "23": "Dark Yellow",
    "31": "Light Orange",
    "32": "Orange",
    "33": "Dark Orange",
    "41": "Light Red",
    "42": "Red",
    "43": "Dark Red",
    "51": "Light Pink",
    "52": "Pink",
    "53": "Dark Pink",
    "61": "Light Purple",
    "62": "Purple",
    "63": "Dark Purple",
    "71": "Light Blue",
    "72": "Blue",
    "73": "Dark Blue",
    "81": "Light Turquoise",
    "82": "Turquoise",
    "83": "Dark Turquoise",
    "91": "Light Green",
    "92": "Green",
    "93": "Dark Green",
}

# User-facing Vietnamese/English synonyms mapped to the canonical dataset code/name.
COLOR_CODE_MAP: Dict[str, Tuple[str, str]] = {
    "bạc": ("03", "Silver"), "silver": ("03", "Silver"),
    "đồng": ("04", "Bronze/Copper"), "bronze": ("04", "Bronze/Copper"), "copper": ("04", "Bronze/Copper"),
    "xám nhạt": ("06", "Light Grey"), "ghi nhạt": ("06", "Light Grey"), "light grey": ("06", "Light Grey"), "light gray": ("06", "Light Grey"),
    "xám": ("07", "Grey"), "ghi": ("07", "Grey"), "grey": ("07", "Grey"), "gray": ("07", "Grey"),
    "xám đậm": ("08", "Dark Grey"), "ghi đậm": ("08", "Dark Grey"), "dark grey": ("08", "Dark Grey"), "dark gray": ("08", "Dark Grey"),
    "đen": ("09", "Black"), "black": ("09", "Black"), "huyền": ("09", "Black"),
    "trắng": ("10", "White"), "white": ("10", "White"), "bạch": ("10", "White"),
    "trắng ngà": ("11", "Off White"), "trắng kem": ("11", "Off White"), "off white": ("11", "Off White"),
    "be nhạt": ("12", "Light Beige"), "light beige": ("12", "Light Beige"),
    "be": ("13", "Beige"), "beige": ("13", "Beige"), "kem": ("13", "Beige"),
    "be đậm": ("14", "Dark Beige"), "dark beige": ("14", "Dark Beige"),
    "be xám": ("15", "Greyish Beige"), "greyish beige": ("15", "Greyish Beige"),
    "nâu vàng": ("17", "Yellowish Brown"), "yellowish brown": ("17", "Yellowish Brown"), "nâu": ("17", "Yellowish Brown"), "brown": ("17", "Yellowish Brown"),
    "kaki xanh": ("19", "Greenish Khaki"), "greenish khaki": ("19", "Greenish Khaki"), "khaki": ("19", "Greenish Khaki"),
    "vàng nhạt": ("21", "Light Yellow"), "light yellow": ("21", "Light Yellow"),
    "vàng": ("22", "Yellow"), "yellow": ("22", "Yellow"),
    "vàng đậm": ("23", "Dark Yellow"), "dark yellow": ("23", "Dark Yellow"),
    "cam nhạt": ("31", "Light Orange"), "light orange": ("31", "Light Orange"),
    "cam": ("32", "Orange"), "orange": ("32", "Orange"),
    "cam đậm": ("33", "Dark Orange"), "dark orange": ("33", "Dark Orange"),
    "đỏ nhạt": ("41", "Light Red"), "light red": ("41", "Light Red"),
    "đỏ": ("42", "Red"), "red": ("42", "Red"),
    "đỏ đậm": ("43", "Dark Red"), "đỏ đô": ("43", "Dark Red"), "đỏ rượu": ("43", "Dark Red"), "dark red": ("43", "Dark Red"), "maroon": ("43", "Dark Red"),
    "hồng nhạt": ("51", "Light Pink"), "light pink": ("51", "Light Pink"),
    "hồng": ("52", "Pink"), "pink": ("52", "Pink"),
    "hồng đậm": ("53", "Dark Pink"), "dark pink": ("53", "Dark Pink"),
    "tím nhạt": ("61", "Light Purple"), "light purple": ("61", "Light Purple"),
    "tím": ("62", "Purple"), "purple": ("62", "Purple"), "violet": ("62", "Purple"),
    "tím đậm": ("63", "Dark Purple"), "dark purple": ("63", "Dark Purple"),
    "xanh dương nhạt": ("71", "Light Blue"), "xanh da trời": ("71", "Light Blue"), "light blue": ("71", "Light Blue"),
    "xanh dương": ("72", "Blue"), "xanh lam": ("72", "Blue"), "blue": ("72", "Blue"),
    "xanh dương đậm": ("73", "Dark Blue"), "xanh navy": ("73", "Dark Blue"), "xanh đen": ("73", "Dark Blue"), "navy": ("73", "Dark Blue"), "dark blue": ("73", "Dark Blue"),
    "xanh ngọc nhạt": ("81", "Light Turquoise"), "light turquoise": ("81", "Light Turquoise"),
    "xanh ngọc": ("82", "Turquoise"), "turquoise": ("82", "Turquoise"),
    "xanh ngọc đậm": ("83", "Dark Turquoise"), "dark turquoise": ("83", "Dark Turquoise"),
    "xanh lá nhạt": ("91", "Light Green"), "light green": ("91", "Light Green"),
    "xanh lá": ("92", "Green"), "green": ("92", "Green"), "lục": ("92", "Green"),
    "xanh lá đậm": ("93", "Dark Green"), "dark green": ("93", "Dark Green"),
}

# Controlled relaxation stays inside the same dataset color family.
COLOR_FAMILY_MAP: Dict[str, List[str]] = {
    "03": ["03", "06", "07"],
    "04": ["04", "17"],
    "06": ["06", "07", "08"], "07": ["06", "07", "08"], "08": ["06", "07", "08", "09"],
    "09": ["09", "08"],
    "10": ["10", "11"], "11": ["10", "11", "12"],
    "12": ["12", "13", "14", "15"], "13": ["12", "13", "14", "15"], "14": ["12", "13", "14", "15"], "15": ["12", "13", "14", "15"],
    "17": ["17", "14", "19"], "19": ["19", "17"],
    "21": ["21", "22", "23"], "22": ["21", "22", "23"], "23": ["21", "22", "23"],
    "31": ["31", "32", "33"], "32": ["31", "32", "33"], "33": ["31", "32", "33"],
    "41": ["41", "42", "43"], "42": ["41", "42", "43"], "43": ["41", "42", "43"],
    "51": ["51", "52", "53"], "52": ["51", "52", "53"], "53": ["51", "52", "53"],
    "61": ["61", "62", "63"], "62": ["61", "62", "63"], "63": ["61", "62", "63"],
    "71": ["71", "72", "73"], "72": ["71", "72", "73"], "73": ["71", "72", "73"],
    "81": ["81", "82", "83"], "82": ["81", "82", "83"], "83": ["81", "82", "83"],
    "91": ["91", "92", "93"], "92": ["91", "92", "93"], "93": ["91", "92", "93"],
}

# Standard category keywords mapped to (group_name, sub_category)
CATEGORY_KEYWORD_MAP: Dict[str, Tuple[str, str]] = {
    "áo thun": ("Garment Upper body", "T-shirt"),
    "áo phông": ("Garment Upper body", "T-shirt"),
    "t-shirt": ("Garment Upper body", "T-shirt"),
    "tshirt": ("Garment Upper body", "T-shirt"),
    "áo sơ mi": ("Garment Upper body", "Shirt"),
    "sơ mi": ("Garment Upper body", "Shirt"),
    "shirt": ("Garment Upper body", "Shirt"),
    "áo len": ("Garment Upper body", "Sweater"),
    "sweater": ("Garment Upper body", "Sweater"),
    "áo blouse": ("Garment Upper body", "Blouse"),
    "blouse": ("Garment Upper body", "Blouse"),
    "áo hoodie": ("Garment Upper body", "Hoodie"),
    "hoodie": ("Garment Upper body", "Hoodie"),
    "áo khoác blazer": ("Garment Upper body", "Blazer"),
    "blazer": ("Garment Upper body", "Blazer"),
    "áo măng tô": ("Garment Upper body", "Coat"),
    "coat": ("Garment Upper body", "Coat"),
    "áo cardigan": ("Garment Upper body", "Cardigan"),
    "cardigan": ("Garment Upper body", "Cardigan"),
    "áo polo": ("Garment Upper body", "Polo shirt"),
    "polo shirt": ("Garment Upper body", "Polo shirt"),
    "áo ba lỗ": ("Garment Upper body", "Vest top"),
    "tank top": ("Garment Upper body", "Vest top"),
    "vest top": ("Garment Upper body", "Vest top"),
    "bodysuit": ("Garment Upper body", "Bodysuit"),
    "áo gile": ("Garment Upper body", "Tailored Waistcoat"),
    "waistcoat": ("Garment Upper body", "Tailored Waistcoat"),
    "áo khoác": ("Garment Upper body", "Jacket"),
    "jacket": ("Garment Upper body", "Jacket"),
    "quần jean": ("Garment Lower body", "Trousers"),
    "quần bò": ("Garment Lower body", "Trousers"),
    "quần tây": ("Garment Lower body", "Trousers"),
    "quần dài": ("Garment Lower body", "Trousers"),
    "quần jogger": ("Garment Lower body", "Trousers"),
    "quần chinos": ("Garment Lower body", "Trousers"),
    "quần chino": ("Garment Lower body", "Trousers"),
    "quần ống rộng": ("Garment Lower body", "Trousers"),
    "quần short": ("Garment Lower body", "Shorts"),
    "quần shorts": ("Garment Lower body", "Shorts"),
    "quần đùi": ("Garment Lower body", "Shorts"),
    "quần ngắn": ("Garment Lower body", "Shorts"),
    "quần soóc": ("Garment Lower body", "Shorts"),
    "quần sọt": ("Garment Lower body", "Shorts"),
    "short pants": ("Garment Lower body", "Shorts"),
    "shorts": ("Garment Lower body", "Shorts"),
    "trousers": ("Garment Lower body", "Trousers"),
    "pants": ("Garment Lower body", "Trousers"),
    # Generic Vietnamese "quần" means the pants family. The image pipeline
    # can still refine it to Trousers or Shorts when a reference image exists.
    "quần": ("Garment Lower body", "Pants"),
    "váy": ("Garment Full body", "Dress"),
    "đầm": ("Garment Full body", "Dress"),
    "dress": ("Garment Full body", "Dress"),
    "jumpsuit": ("Garment Full body", "Jumpsuit/Playsuit"),
    "playsuit": ("Garment Full body", "Jumpsuit/Playsuit"),
    "chân váy": ("Garment Lower body", "Skirt"),
    "skirt": ("Garment Lower body", "Skirt"),
    "giày boots": ("Shoes", "Boots"),
    "boots": ("Shoes", "Boots"),
    "sneaker": ("Shoes", "Sneakers"),
    "sneakers": ("Shoes", "Sneakers"),
    "giày sneaker": ("Shoes", "Sneakers"),
    "giày thể thao": ("Shoes", "Sneakers"),
    "giày búp bê": ("Shoes", "Ballerinas"),
    "ballerinas": ("Shoes", "Ballerinas"),
    "giày cao gót": ("Shoes", "Pumps"),
    "pumps": ("Shoes", "Pumps"),
    "dép lê": ("Shoes", "Slippers"),
    "slippers": ("Shoes", "Slippers"),
    "dép xỏ ngón": ("Shoes", "Flip flop"),
    "flip flop": ("Shoes", "Flip flop"),
    "dép cao gót": ("Shoes", "Heeled sandals"),
    "heeled sandals": ("Shoes", "Heeled sandals"),
    "giày đế xuồng": ("Shoes", "Wedge"),
    "wedge": ("Shoes", "Wedge"),
    "flat shoes": ("Shoes", "Flat shoe"),
    "flat shoe": ("Shoes", "Flat shoe"),
    "sandal": ("Shoes", "Sandals"),
    "sandals": ("Shoes", "Sandals"),
    "dép sandal": ("Shoes", "Sandals"),
    # Generic footwear terms deliberately map to the catalog group instead
    # of guessing Sneakers or Sandals.
    "giày": ("Shoes", "Shoes"),
    "dép": ("Shoes", "Shoes"),
}

CATALOG_CATEGORIES = {
    "Garment Upper body", "Garment Lower body", "Garment Full body", "Shoes",
    "T-shirt", "Sweater", "Shirt", "Blouse", "Top", "Jacket", "Hoodie",
    "Vest top", "Blazer", "Polo shirt", "Cardigan", "Coat", "Bodysuit",
    "Tailored Waistcoat", "Pants", "Trousers", "Shorts", "Skirt", "Dress",
    "Jumpsuit/Playsuit", "Boots", "Sneakers", "Other shoe", "Sandals",
    "Flat shoe", "Ballerinas", "Pumps", "Slippers", "Flip flop",
    "Heeled sandals", "Wedge",
}

# Standard fashion materials
MATERIAL_SYNONYMS: Dict[str, str] = {
    "da": "leather",
    "leather": "leather",
    "bò": "denim",
    "jean": "denim",
    "denim": "denim",
    "cotton": "cotton",
    "thun": "cotton",
    "len": "wool",
    "wool": "wool",
    "lụa": "silk",
    "silk": "silk",
    "kaki": "cotton",
    "dù": "nylon",
    "nylon": "nylon",
    "polyester": "polyester",
    "canvas": "canvas",
    "vải bố": "canvas",
}


class EntityNormalizer:
    """Normalizes natural queries into canonical database attributes."""

    @staticmethod
    def normalize_phonetics(text: str) -> str:
        """Corrects phonetic and dialect typos common across Vietnamese regions."""
        if not text:
            return ""
        result = text.strip()
        for pattern, replacement in DIALECT_REPLACEMENTS:
            result = pattern.sub(replacement, result)
        return result

    @staticmethod
    def extract_color(text: str) -> Optional[Tuple[str, str]]:
        """Finds color mention in text and returns (color_code, color_name)."""
        lower = text.lower()
        # Sort keys by length descending to match composite colors first (e.g., 'xanh navy' before 'xanh')
        for synonym in sorted(COLOR_CODE_MAP.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(synonym) + r"\b", lower):
                return COLOR_CODE_MAP[synonym]
        return None

    @staticmethod
    def get_color_code(color_query: str) -> Optional[str]:
        """Resolves a color name, synonym, or code to the dataset color code."""
        if not color_query:
            return None
        raw = color_query.strip()
        if raw in COLOR_NAME_BY_CODE:
            return raw
        if raw.isdigit():
            padded = raw.zfill(2)
            if padded in COLOR_NAME_BY_CODE:
                return padded
        found = EntityNormalizer.extract_color(raw)
        if found:
            return found[0]
        lower = raw.lower()
        for code, name in COLOR_NAME_BY_CODE.items():
            if lower == name.lower():
                return code
        return None

    @staticmethod
    def get_color_name(color_code: str) -> str:
        """Returns the canonical dataset color name for a stored code."""
        raw = str(color_code).strip()
        if raw != "-1" and raw.isdigit():
            raw = raw.zfill(2)
        return COLOR_NAME_BY_CODE.get(raw, str(color_code))

    @staticmethod
    def get_color_family(color_query: str) -> List[str]:
        """Returns dataset codes in the same color family for controlled relaxation."""
        if not color_query:
            return []
        code = EntityNormalizer.get_color_code(color_query)
        if not code:
            return []
        return COLOR_FAMILY_MAP.get(code, [code])

    @staticmethod
    def extract_category(text: str) -> Optional[Tuple[str, str]]:
        """Finds category mention in text and returns (group_name, sub_category)."""
        lower = text.lower()
        for kw in sorted(CATEGORY_KEYWORD_MAP.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return CATEGORY_KEYWORD_MAP[kw]
        return None

    @staticmethod
    def normalize_category(category: str) -> Optional[str]:
        """Validates and canonicalizes a category against the catalog taxonomy."""
        if not category:
            return None
        raw = category.strip()
        for canonical in CATALOG_CATEGORIES:
            if raw.lower() == canonical.lower():
                return canonical
        found = EntityNormalizer.extract_category(raw)
        return found[1] if found else None

    @staticmethod
    def normalize_material(text: str) -> Optional[str]:
        """Maps freeform material mention to standardized canonical English name."""
        lower = text.lower()
        for syn, canonical in sorted(MATERIAL_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(syn) + r"\b", lower):
                return canonical
        return None

    @staticmethod
    def normalize_gender(text: str) -> Optional[str]:
        """Maps Vietnamese/English gender labels to the values used by QueryIntent."""
        lower = text.strip().lower()
        if lower in {"menswear", "men", "male", "nam", "đàn ông", "trai"}:
            return "Menswear"
        if lower in {"ladieswear", "women", "woman", "female", "nữ", "phụ nữ", "gái"}:
            return "Ladieswear"
        if lower in {"unisex", "cả nam và nữ", "nam nữ"}:
            return "Unisex"
        return None

    @staticmethod
    def extract_gender(text: str) -> Optional[str]:
        """Extracts gender only when the user explicitly mentions it."""
        lower = text.lower()
        patterns = [
            (r"\b(?:unisex|nam\s*nữ|cả\s+nam\s+và\s+nữ)\b", "Unisex"),
            (r"\b(?:phụ\s*nữ|nữ|đàn\s*bà|girl|girls|woman|women|ladies)\b", "Ladieswear"),
            (r"\b(?:đàn\s*ông|nam|trai|boy|boys|man|men)\b", "Menswear"),
        ]
        for pattern, canonical in patterns:
            if re.search(pattern, lower):
                return canonical
        return None

    @staticmethod
    def parse_vnd_price(text: str) -> Optional[int]:
        """Extracts numeric price from natural Vietnamese text.
        
        Handles: 'dưới 1 triệu', '1.5tr', '1,5 triệu', '500k', '800 nghìn', '1.200.000'.
        """
        lower = text.lower()
        
        # Match 'X.Y triệu' or 'X.Y tr' or 'X,Y tr' (decimal million)
        match_mil_dec = re.search(r"(\d+(?:[.,]\d+)?)\s*(triệu|tr|m)\b", lower)
        if match_mil_dec:
            val_str = match_mil_dec.group(1).replace(",", ".")
            return int(float(val_str) * 1_000_000)

        # Match 'X k' or 'X nghìn'
        match_k = re.search(r"(\d+(?:[.,]\d+)?)\s*(k|nghìn|ngàn)\b", lower)
        if match_k:
            val_str = match_k.group(1).replace(",", ".")
            return int(float(val_str) * 1_000)

        # Match formatted explicit digits like 1.200.000 or 500,000 or raw 499000
        clean_text = lower.replace(".", "").replace(",", "")
        match_digits = re.search(r"\b(\d{5,8})\b", clean_text)
        if match_digits:
            return int(match_digits.group(1))

        return None
