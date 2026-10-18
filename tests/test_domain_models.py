"""Unit Test Suite for Domain Models.

Verifies the 14 Domain Classes and their methods:
Customer, Category, Product, SearchQuery, TextQuery, ImageQuery, VoiceQuery,
SearchResult, Cart, CartItem, Order, OrderItem, Payment, Shipment.
"""

from __future__ import annotations

import pytest
from backend.domain.models import (
    Customer,
    Category,
    Product,
    SearchQuery,
    TextQuery,
    ImageQuery,
    VoiceQuery,
    SearchResult,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Payment,
    Shipment,
)


def test_customer_update_profile():
    c = Customer(full_name="Nguyen Van A", email="a@example.com")
    c.update_profile(full_name="Nguyen Van B", age=25, phone_number="0912345678")
    assert c.full_name == "Nguyen Van B"
    assert c.age == 25
    assert c.phone_number == "0912345678"

    with pytest.raises(ValueError, match="Age must be non-negative"):
        c.update_profile(age=-1)


def test_query_validation_hierarchy():
    t_valid = TextQuery(query_text="áo khoác")
    t_invalid = TextQuery(query_text="  ")
    assert t_valid.validate() is True
    assert t_invalid.validate() is False

    img_valid = ImageQuery(image_reference="uploads/img1.jpg", selected_region="[0,0,1,1]")
    img_invalid = ImageQuery(image_reference="")
    assert img_valid.validate() is True
    assert img_invalid.validate() is False

    voice_valid = VoiceQuery(transcribe_text="quần jean nam", audio_reference="uploads/rec.webm")
    voice_invalid = VoiceQuery(transcribe_text="")
    assert voice_valid.validate() is True
    assert voice_invalid.validate() is False


def test_search_result_and_product():
    p = Product(
        article_id="0123456789",
        product_name="Áo thun",
        price=299000,
        image_path="images/0123456789.jpg",
        image_embedding=[0.1] * 768,
        text_embedding=[0.2] * 768,
    )
    res = SearchResult(article_id=p.article_id, rank=1, score=0.95)
    assert res.rank == 1
    assert res.score == 0.95
    assert len(p.image_embedding) == 768


def test_cart_operations():
    cart = Cart()
    item1 = cart.add_item(article_id="0123456789", quantity=2, unit_price=100000)
    assert item1.calculate_subtotal() == 200000
    assert cart.calculate_total() == 200000

    # Add same item increases quantity
    cart.add_item(article_id="0123456789", quantity=1, unit_price=100000)
    assert cart.calculate_total() == 300000

    # Add different item
    cart.add_item(article_id="9876543210", quantity=1, unit_price=50000)
    assert cart.calculate_total() == 350000

    # Remove item
    cart.remove_item(article_id="0123456789")
    assert len(cart.items) == 1
    assert cart.calculate_total() == 50000


def test_order_payment_shipment_operations():
    order = Order(total_amount=500000)
    order.update_status("processing")
    assert order.status == "processing"

    order_item = OrderItem(order_id=order.order_id, article_id="0123456789", quantity=2, unit_price=250000)
    assert order_item.calculate_subtotal() == 500000

    payment = Payment(order_id=order.order_id, amount=500000)
    payment.mark_paid(transaction_code="TX123456")
    assert payment.status == "completed"
    assert payment.paid_at is not None

    shipment = Shipment(order_id=order.order_id, tracking_number="VN123456789")
    shipment.update_status("delivered")
    assert shipment.status == "delivered"
    assert shipment.delivered_at is not None
