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

# Color synonyms dictionary mapped to H&M color code and canonical English name
COLOR_CODE_MAP: Dict[str, Tuple[str, str]] = {
    # 09: Black
    "đen": ("09", "Black"),
    "black": ("09", "Black"),
    "huyền": ("09", "Black"),
    "tối": ("09", "Black"),
    # 10: White
    "trắng": ("10", "White"),
    "white": ("10", "White"),
    "bạch": ("10", "White"),
    "sáng": ("10", "White"),
    # 06: Light Grey
    "xám": ("06", "Grey"),
    "ghi": ("06", "Grey"),
    "grey": ("06", "Grey"),
    "gray": ("06", "Grey"),
    # 14: Dark Blue / Navy
    "xanh navy": ("14", "Dark Blue"),
    "navy": ("14", "Dark Blue"),
    "xanh đen": ("14", "Dark Blue"),
    "xanh thẫm": ("14", "Dark Blue"),
    # 12: Blue
    "xanh dương": ("12", "Blue"),
    "blue": ("12", "Blue"),
    "xanh lam": ("12", "Blue"),
    # 71: Light Blue
    "xanh nhạt": ("71", "Light Blue"),
    "xanh da trời": ("71", "Light Blue"),
    "light blue": ("71", "Light Blue"),
    # 02: Beige
    "be": ("02", "Beige"),
    "beige": ("02", "Beige"),
    "kem": ("02", "Beige"),
    # 42: Red
    "đỏ": ("42", "Red"),
    "red": ("42", "Red"),
    # 43: Dark Red
    "đỏ đô": ("43", "Dark Red"),
    "đỏ rượu": ("43", "Dark Red"),
    "maroon": ("43", "Dark Red"),
    # 51: Pink
    "hồng": ("51", "Pink"),
    "pink": ("51", "Pink"),
    # 73: Green
    "xanh lá": ("73", "Green"),
    "green": ("73", "Green"),
    "lục": ("73", "Green"),
    # 81: Yellow
    "vàng": ("81", "Yellow"),
    "yellow": ("81", "Yellow"),
    # 31: Orange
    "cam": ("31", "Orange"),
    "orange": ("31", "Orange"),
    # 21: Brown
    "nâu": ("21", "Brown"),
    "brown": ("21", "Brown"),
}

# Color family taxonomy mapping color code/canonical -> list of related colors (chromatic proximity)
COLOR_FAMILY_MAP: Dict[str, List[str]] = {
    "02": ["02", "11", "10", "19", "Beige", "Light Beige", "Dark Beige", "Greyish Beige", "Off White", "Khaki", "Greenish Khaki", "White", "Cream"],
    "10": ["10", "11", "02", "White", "Off White", "Light Beige", "Light Grey"],
    "09": ["09", "08", "06", "Black", "Dark Grey", "Grey", "Charcoal"],
    "06": ["06", "08", "07", "Grey", "Light Grey", "Dark Grey", "Melange"],
    "14": ["14", "12", "71", "72", "73", "Dark Blue", "Blue", "Light Blue", "Navy", "Turquoise"],
    "12": ["12", "14", "71", "72", "73", "Blue", "Dark Blue", "Light Blue", "Navy", "Turquoise"],
    "71": ["71", "12", "72", "Light Blue", "Blue", "Turquoise", "Light Turquoise"],
    "42": ["42", "43", "51", "52", "Red", "Dark Red", "Pink", "Burgundy", "Maroon"],
    "43": ["43", "42", "Dark Red", "Red", "Maroon", "Burgundy"],
    "51": ["51", "52", "42", "Pink", "Light Pink", "Red"],
    "73": ["73", "19", "Green", "Dark Green", "Light Green", "Khaki", "Greenish Khaki"],
    "21": ["21", "14", "02", "Brown", "Dark Brown", "Dark Beige", "Camel"],
    "81": ["81", "22", "31", "Yellow", "Light Yellow", "Orange"],
    "31": ["31", "81", "Orange", "Light Orange", "Yellow"],
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
    "hoodie": ("Garment Upper body", "Hoodie"),
    "áo khoác": ("Nightwear", "Jacket"),
    "jacket": ("Nightwear", "Jacket"),
    "blazer": ("Nightwear", "Jacket"),
    "quần jean": ("Garment Lower body", "Trousers"),
    "quần bò": ("Garment Lower body", "Trousers"),
    "quần tây": ("Garment Lower body", "Trousers"),
    "quần dài": ("Garment Lower body", "Trousers"),
    "quần short": ("Garment Lower body", "Shorts"),
    "quần đùi": ("Garment Lower body", "Shorts"),
    "váy": ("Garment Full body", "Dress"),
    "đầm": ("Garment Full body", "Dress"),
    "dress": ("Garment Full body", "Dress"),
    "chân váy": ("Garment Lower body", "Skirt"),
    "skirt": ("Garment Lower body", "Skirt"),
    "giày": ("Shoes", "Sneakers"),
    "sneaker": ("Shoes", "Sneakers"),
    "giày sneaker": ("Shoes", "Sneakers"),
    "giày thể thao": ("Shoes", "Sneakers"),
    "dép": ("Shoes", "Sandals"),
    "sandal": ("Shoes", "Sandals"),
    "túi": ("Bags", "Handbag"),
    "túi xách": ("Bags", "Handbag"),
    "balo": ("Bags", "Backpack"),
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
    def get_color_family(color_query: str) -> List[str]:
        """Returns related/similar colors for a given color name or code (relaxation fallback)."""
        if not color_query:
            return []
        norm = color_query.strip().lower()
        # Find code if name was passed
        code = None
        if norm in COLOR_CODE_MAP:
            code = COLOR_CODE_MAP[norm][0]
        else:
            for c_code, c_names in COLOR_FAMILY_MAP.items():
                if any(norm == name.lower() for name in c_names):
                    code = c_code
                    break

        if code and code in COLOR_FAMILY_MAP:
            return COLOR_FAMILY_MAP[code]
        return [color_query]

    @staticmethod
    def extract_category(text: str) -> Optional[Tuple[str, str]]:
        """Finds category mention in text and returns (group_name, sub_category)."""
        lower = text.lower()
        for kw in sorted(CATEGORY_KEYWORD_MAP.keys(), key=len, reverse=True):
            if re.search(r"\b" + re.escape(kw) + r"\b", lower):
                return CATEGORY_KEYWORD_MAP[kw]
        return None

    @staticmethod
    def normalize_material(text: str) -> Optional[str]:
        """Maps freeform material mention to standardized canonical English name."""
        lower = text.lower()
        for syn, canonical in sorted(MATERIAL_SYNONYMS.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(r"\b" + re.escape(syn) + r"\b", lower):
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
