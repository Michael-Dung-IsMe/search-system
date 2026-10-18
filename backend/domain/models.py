"""Domain Model Classes for E-Commerce Fashion AI Search System.

Directly reflects the 14 UML Design Classes from Visual Paradigm:
Customer, Category, Product, SearchQuery, TextQuery, ImageQuery, VoiceQuery,
SearchResult, Cart, CartItem, Order, OrderItem, Payment, Shipment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


@dataclass
class Customer:
    """Customer entity representation."""

    id: UUID = field(default_factory=uuid4)
    full_name: str = ""
    email: str = ""
    age: Optional[int] = None
    phone_number: Optional[str] = None
    shipping_address: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_profile(
        self,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        shipping_address: Optional[str] = None,
        age: Optional[int] = None,
    ) -> None:
        """Updates profile details with validated values."""
        if full_name:
            self.full_name = full_name
        if phone_number:
            self.phone_number = phone_number
        if shipping_address:
            self.shipping_address = shipping_address
        if age is not None:
            if age < 0:
                raise ValueError("Age must be non-negative.")
            self.age = age
        self.updated_at = datetime.utcnow()


@dataclass
class Category:
    """Product Category classification."""

    id: int
    group_name: str
    sub_category: str


@dataclass
class Product:
    """Product entity with embedded multimodal vector features."""

    article_id: str
    product_name: str
    price: float
    image_path: str
    category_id: Optional[int] = None
    product_code: Optional[str] = None
    color_code: Optional[str] = None
    gender: Optional[str] = None
    detail_desc: Optional[str] = None
    image_embedding: Optional[List[float]] = None
    text_embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """Ranked item association belonging to a SearchQuery."""

    article_id: str
    rank: int
    score: float
    id: Optional[int] = None
    query_id: Optional[UUID] = None


@dataclass
class SearchQuery:
    """Abstract/Parent query class representing a search request."""

    query_id: UUID = field(default_factory=uuid4)
    customer_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    search_criteria: Optional[str] = None
    results: List[SearchResult] = field(default_factory=list)

    def validate(self) -> bool:
        """Validates query invariants."""
        return True


@dataclass
class TextQuery(SearchQuery):
    """Text-based query."""

    query_text: str = ""

    def validate(self) -> bool:
        """Validates that query_text is non-empty."""
        return bool(self.query_text and self.query_text.strip())


@dataclass
class ImageQuery(SearchQuery):
    """Image-based visual query with optional bounding region."""

    image_reference: str = ""
    selected_region: Optional[str] = None

    def validate(self) -> bool:
        """Validates that an image reference exists."""
        return bool(self.image_reference and self.image_reference.strip())


@dataclass
class VoiceQuery(SearchQuery):
    """Voice/Speech query with audio blob and transcript."""

    transcribe_text: str = ""
    audio_reference: Optional[str] = None

    def validate(self) -> bool:
        """Validates that transcription text is available."""
        return bool(self.transcribe_text and self.transcribe_text.strip())


@dataclass
class CartItem:
    """Individual item inside a shopping cart."""

    id: Optional[int] = None
    cart_id: Optional[UUID] = None
    article_id: str = ""
    quantity: int = 1
    unit_price: float = 0.0

    def calculate_subtotal(self) -> float:
        """Calculates line item subtotal."""
        return self.quantity * self.unit_price


@dataclass
class Cart:
    """Customer shopping cart."""

    id: UUID = field(default_factory=uuid4)
    customer_id: Optional[UUID] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    items: List[CartItem] = field(default_factory=list)

    def add_item(self, article_id: str, quantity: int = 1, unit_price: float = 0.0) -> CartItem:
        """Adds or updates item quantity in cart."""
        for item in self.items:
            if item.article_id == article_id:
                item.quantity += quantity
                return item
        new_item = CartItem(cart_id=self.id, article_id=article_id, quantity=quantity, unit_price=unit_price)
        self.items.append(new_item)
        return new_item

    def remove_item(self, article_id: str) -> None:
        """Removes an item from cart."""
        self.items = [item for item in self.items if item.article_id != article_id]

    def calculate_total(self) -> float:
        """Computes aggregate cart cost."""
        return sum(item.calculate_subtotal() for item in self.items)


@dataclass
class OrderItem:
    """OrderItem snapshot at checkout."""

    id: Optional[int] = None
    order_id: Optional[UUID] = None
    article_id: str = ""
    quantity: int = 1
    unit_price: float = 0.0

    def calculate_subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Order:
    """E-commerce purchase order."""

    order_id: UUID = field(default_factory=uuid4)
    customer_id: Optional[UUID] = None
    status: str = "pending"
    total_amount: float = 0.0
    shipping_address: str = ""
    recipient_phone: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    items: List[OrderItem] = field(default_factory=list)

    def update_status(self, new_status: str) -> None:
        """Transitions order status."""
        self.status = new_status


@dataclass
class Payment:
    """Payment transaction details."""

    payment_id: UUID = field(default_factory=uuid4)
    order_id: Optional[UUID] = None
    payment_method: str = "cod"
    amount: float = 0.0
    status: str = "pending"
    transaction_code: Optional[str] = None
    paid_at: Optional[datetime] = None

    def mark_paid(self, transaction_code: str) -> None:
        """Marks payment completed."""
        self.status = "completed"
        self.transaction_code = transaction_code
        self.paid_at = datetime.utcnow()


@dataclass
class Shipment:
    """Shipment and delivery tracking."""

    shipment_id: UUID = field(default_factory=uuid4)
    order_id: Optional[UUID] = None
    tracking_number: Optional[str] = None
    carrier: str = "GiaoHangNhanh"
    status: str = "preparing"
    estimated_delivery_date: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    def update_status(self, new_status: str) -> None:
        self.status = new_status
        if new_status == "delivered":
            self.delivered_at = datetime.utcnow()
