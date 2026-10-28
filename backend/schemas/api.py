"""Pydantic API request and response models for REST endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.schemas.state import ConstraintChip, SearchResponse, SearchResultItem, SearchState


class DetectedBox(BaseModel):
    """Normalized bounding box detected by OWL-ViT."""
    box_id: str = Field(..., description="Unique box ID")
    label: str = Field(..., description="Coarse garment-region label, e.g. UpperGarment, Pants, Skirt, Dress, Shoes")
    score: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    box_2d: List[float] = Field(..., min_length=4, max_length=4, description="[ymin, xmin, ymax, xmax] normalized to [0.0, 1.0]")
    polygon: Optional[List[List[float]]] = Field(
        default=None,
        description="Normalized [x, y] polygon vertices tracing garment contour for SVG glow highlighting"
    )


class DetectResponse(BaseModel):
    """Response returned by /api/detect."""
    image_hash: str
    total_boxes: int
    boxes: List[DetectedBox]


class TranscribeResponse(BaseModel):
    """Response returned by /api/transcribe."""
    text: str
    language: str = "vi"


class DeleteConstraintRequest(BaseModel):
    """Request payload to remove an active constraint chip."""
    session_id: str
    chip_id: str


class ProductDetailResponse(BaseModel):
    """Detailed product information returned by /api/products/{id}."""
    article_id: str
    product_code: str
    prod_name: str
    price_vnd: int
    gender: str
    color_code: str
    color_name: str
    category_group: str
    category_sub: str
    detail_desc: str
    image_path: str


class ErrorResponse(BaseModel):
    """Standardized structured error model for consistent client error handling."""
    error_type: str
    message: str
    detail: Optional[str] = None
    status_code: int
