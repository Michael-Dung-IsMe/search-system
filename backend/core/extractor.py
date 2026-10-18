"""Intent Extractor using LLM (OpenAI / Gemini) with Rule-based Local Fallback.

Extracts structured QueryIntent containing categories, colors, price ranges,
and negative constraints (excludes) with dialect & phonetic normalization.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from backend.core.normalizer import EntityNormalizer
from backend.schemas.state import QueryIntent

load_dotenv()
logger = logging.getLogger("intent_extractor")

SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên gia trích xuất ý định tìm kiếm thời trang đa phương thức.
Nhiệm vụ của bạn:
1. Sửa lỗi phát âm, phương ngữ 3 miền Bắc/Trung/Nam (ví dụ: 'dày da' -> 'giày da', 'bận' -> 'mặc', 'chiệu/chẹo' -> 'triệu').
2. Trích xuất thông tin có cấu trúc:
   - category: tên loại sản phẩm (ví dụ: 'T-shirt', 'Jacket', 'Trousers', 'Sneakers', 'Handbag', 'Dress').
   - gender: 'Ladieswear' hoặc 'Menswear' hoặc 'Unisex'.
   - color: màu sắc người dùng muốn.
   - min_price / max_price: giá trị VND (số nguyên, ví dụ: 1 triệu -> 1000000, 500k -> 500000).
   - material: chất liệu mong muốn (cotton, denim, leather, canvas, silk...).
   - style: phong cách (sport, formal, casual, vintage...).
   - purpose: mục đích (đi tiệc, đi làm, chạy bộ...).
   - exclude_colors: danh sách màu NGƯỜI DÙNG KHÔNG MUỐN (ví dụ: 'không màu đen' -> ['09' hoặc 'Black']).
   - exclude_materials: danh sách chất liệu NGƯỜI DÙNG KHÔNG MUỐN (ví dụ: 'không phải da' -> ['leather']).
   - reference_ordinal: số thứ tự sản phẩm tham chiếu (ví dụ: 'giống số 1' -> 1, 'đôi thứ 2' -> 2).

Chỉ trả về JSON hợp lệ theo định dạng Schema được yêu cầu."""


class IntentExtractor:
    """Extracts QueryIntent with multi-provider fallback strategy."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        use_mock: bool = False,
    ):
        self.use_mock = use_mock
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.gemini_key = gemini_api_key or os.getenv("GEMINI_API_KEY")

    def extract(self, query_text: str) -> QueryIntent:
        """Extracts QueryIntent from raw user query text."""
        if not query_text or not query_text.strip():
            return QueryIntent(raw_query="", normalized_query="")

        # 1. Phonetic normalization preprocessing
        normalized_text = EntityNormalizer.normalize_phonetics(query_text)

        if self.use_mock:
            return self._extract_rule_based(query_text, normalized_text)

        # 2. Try OpenAI gpt-4o-mini if key available
        if self.openai_key:
            try:
                return self._extract_openai(query_text, normalized_text)
            except Exception as e:
                logger.warning("OpenAI extraction failed (%s), attempting Gemini fallback...", e)

        # 3. Try Gemini Flash fallback if key available
        if self.gemini_key:
            try:
                return self._extract_gemini(query_text, normalized_text)
            except Exception as e:
                logger.warning("Gemini extraction failed (%s), attempting rule-based fallback...", e)

        # 4. Final resilient fallback: Rule-based local extractor
        return self._extract_rule_based(query_text, normalized_text)

    def _extract_openai(self, raw_query: str, normalized_text: str) -> QueryIntent:
        """Uses OpenAI structured outputs API."""
        from openai import OpenAI

        client = OpenAI(api_key=self.openai_key)
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Truy vấn: {normalized_text}"},
            ],
            response_format=QueryIntent,
        )
        intent = response.choices[0].message.parsed
        if intent:
            intent.raw_query = raw_query
            intent.normalized_query = normalized_text
            if intent.color:
                norm_c = EntityNormalizer.extract_color(intent.color)
                if norm_c:
                    intent.color = norm_c[1]
            if intent.category:
                norm_cat = EntityNormalizer.extract_category(intent.category)
                if norm_cat:
                    intent.category = norm_cat[1]
            if intent.gender:
                norm_g = EntityNormalizer.normalize_gender(intent.gender)
                if norm_g:
                    intent.gender = norm_g
            return intent
        return self._extract_rule_based(raw_query, normalized_text)

    def _extract_gemini(self, raw_query: str, normalized_text: str) -> QueryIntent:
        """Uses Google Gemini API with JSON schema."""
        import google.generativeai as genai

        genai.configure(api_key=self.gemini_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config={"response_mime_type": "application/json"},
        )
        prompt = f"{SYSTEM_PROMPT}\n\nTruy vấn của người dùng: {normalized_text}\nTrả về JSON với các trường: category, gender, color, min_price, max_price, material, style, purpose, exclude_colors, exclude_materials, reference_ordinal."
        response = model.generate_content(prompt)
        data = json.loads(response.text)

        raw_color = data.get("color")
        canonical_color = None
        if raw_color:
            norm_c = EntityNormalizer.extract_color(raw_color)
            canonical_color = norm_c[1] if norm_c else raw_color

        raw_cat = data.get("category")
        canonical_cat = None
        if raw_cat:
            norm_cat = EntityNormalizer.extract_category(raw_cat)
            canonical_cat = norm_cat[1] if norm_cat else raw_cat

        raw_gen = data.get("gender")
        canonical_gen = None
        if raw_gen:
            canonical_gen = EntityNormalizer.normalize_gender(raw_gen) or raw_gen

        intent = QueryIntent(
            raw_query=raw_query,
            normalized_query=normalized_text,
            category=canonical_cat,
            gender=canonical_gen,
            color=canonical_color,
            min_price=data.get("min_price"),
            max_price=data.get("max_price"),
            material=data.get("material"),
            style=data.get("style"),
            purpose=data.get("purpose"),
            exclude_colors=data.get("exclude_colors", []),
            exclude_materials=data.get("exclude_materials", []),
            reference_ordinal=data.get("reference_ordinal"),
        )
        return intent

    def _extract_rule_based(self, raw_query: str, normalized_text: str) -> QueryIntent:
        """Local regex & dictionary fallback engine when LLMs are offline."""
        text = normalized_text.lower()
        intent = QueryIntent(raw_query=raw_query, normalized_query=normalized_text)

        # Check negative constraints (không / đừng / trừ / tránh)
        neg_patterns = [
            r"(?:không|đừng|tránh|chớ|ngoại trừ|trừ)\s+(?:phải|màu|chất liệu)?\s*([a-zA-Z\s\w]+)",
        ]
        for pat in neg_patterns:
            for match in re.finditer(pat, text):
                phrase = match.group(1).strip()
                # Check if it's an excluded color
                color_found = EntityNormalizer.extract_color(phrase)
                if color_found:
                    intent.exclude_colors.append(color_found[1])
                # Check if it's an excluded material
                mat_found = EntityNormalizer.normalize_material(phrase)
                if mat_found:
                    intent.exclude_materials.append(mat_found)

        # Positive color (only if not in negative)
        color_found = EntityNormalizer.extract_color(text)
        if color_found and color_found[1] not in intent.exclude_colors:
            intent.color = color_found[1]

        # Positive category
        cat_found = EntityNormalizer.extract_category(text)
        if cat_found:
            intent.category = cat_found[1]

        # Positive material
        mat_found = EntityNormalizer.normalize_material(text)
        if mat_found and mat_found not in intent.exclude_materials:
            intent.material = mat_found

        # Price bounds
        if "dưới" in text or "tối đa" in text or "nhỏ hơn" in text or "dưới " in text:
            intent.max_price = EntityNormalizer.parse_vnd_price(text)
        elif "trên" in text or "tối thiểu" in text or "lớn hơn" in text:
            intent.min_price = EntityNormalizer.parse_vnd_price(text)
        else:
            price = EntityNormalizer.parse_vnd_price(text)
            if price:
                intent.max_price = price

        # Gender detection
        if any(w in text for w in ["nam", "đàn ông", "trai", "boy", "men"]):
            intent.gender = "Menswear"
        elif any(w in text for w in ["nữ", "phụ nữ", "gái", "girl", "ladies"]):
            intent.gender = "Ladieswear"

        # Reference ordinal check: 'giống số 1', 'thứ 2'
        ref_match = re.search(r"(?:giống|như|chiếc|đôi|cái|mẫu)\s+(?:số|thứ)?\s*(\d+)", text)
        if ref_match:
            intent.reference_ordinal = int(ref_match.group(1))

        return intent
