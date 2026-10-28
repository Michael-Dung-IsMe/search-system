"""Pydantic schemas for Multimodal Search State, Intent, and Results.

Defines strict type models adhering to the project's contract-based design.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ConstraintChip(BaseModel):
    """Represents an active interactive filter chip shown in the UI."""
    chip_id: str = Field(..., description="Unique identifier for the chip, e.g. 'color:10' or 'price:1000000'")
    label: str = Field(..., description="Human-readable label, e.g. 'Màu: Trắng' or 'Tối đa: 1.000.000đ'")
    chip_type: Literal["category", "gender", "color", "price", "material", "exclude_color", "exclude_material", "reference"]
    value: Any = Field(..., description="Underlying value represented by the chip")
    is_removable: bool = Field(True, description="Whether the user can click [x] to remove this chip")


class QueryIntent(BaseModel):
    """Structured intent extracted by LLM (OpenAI/Gemini) with Dialect Normalizer."""
    raw_query: str = Field("", description="Raw input text or speech transcript")
    normalized_query: str = Field("", description="Cleaned dialect-normalized text")
    intent_type: Literal["product_search", "conversation"] = Field(
        "product_search",
        description="Whether the user wants fashion products or is only chatting",
    )
    category: Optional[str] = Field(None, description="Target product category, e.g., 'T-shirt', 'Shoes'")
    gender: Optional[Literal["Ladieswear", "Menswear", "Unisex"]] = Field(None, description="Target gender")
    color: Optional[str] = Field(None, description="Preferred color name or code")
    min_price: Optional[int] = Field(None, ge=0, description="Minimum price in VND")
    max_price: Optional[int] = Field(None, ge=0, description="Maximum price in VND")
    material: Optional[str] = Field(None, description="Preferred material, e.g., 'cotton', 'denim', 'canvas'")
    style: Optional[str] = Field(None, description="Preferred style, e.g., 'sport', 'formal', 'casual'")
    purpose: Optional[str] = Field(None, description="Usage purpose, e.g., 'chạy bộ', 'đi làm'")
    exclude_colors: List[str] = Field(default_factory=list, description="Negative constraint: unwanted colors")
    exclude_materials: List[str] = Field(default_factory=list, description="Negative constraint: unwanted materials")
    reference_ordinal: Optional[int] = Field(None, ge=1, description="Index reference like 'giống số 1', 'chiếc thứ 2'")


class SearchState(BaseModel):
    """Unified conversational search state maintained across multi-turn interactions."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    turn_index: int = Field(0, ge=0)
    category: Optional[str] = None
    gender: Optional[str] = None
    color: Optional[str] = None
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    material: Optional[str] = None
    style: Optional[str] = None
    purpose: Optional[str] = None
    exclude_colors: List[str] = Field(default_factory=list)
    exclude_materials: List[str] = Field(default_factory=list)
    reference_article_id: Optional[str] = None
    active_chips: List[ConstraintChip] = Field(default_factory=list)


class SearchResultItem(BaseModel):
    """Individual item returned in search candidate list."""
    article_id: str
    prod_name: str
    price_vnd: int
    gender: str
    color_code: str
    color_name: str
    category_group: str
    category_sub: str
    image_path: str
    detail_desc: str
    visual_similarity: float = Field(0.0, ge=0.0, le=1.0)
    final_score: float = Field(0.0)
    explanation_badges: List[str] = Field(default_factory=list)
    match_type: Literal["exact", "similar"] = "exact"
    similarity_reason: Optional[str] = None


class SearchResponse(BaseModel):
    """Standardized search response returned to clients."""
    session_id: str
    turn_index: int
    total_results: int
    search_state: SearchState
    items: List[SearchResultItem]
    latency_ms: int = 0
    query_id: Optional[str] = None
    has_exact_match: bool = True
    exact_items: List[SearchResultItem] = Field(default_factory=list)
    similar_items: List[SearchResultItem] = Field(default_factory=list)
    message: Optional[str] = None
    response_type: Literal["search_results", "conversation"] = "search_results"
