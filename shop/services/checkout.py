import json
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

from ..models import Product
from .catalog import to_display_money


MAX_UNIQUE_CART_ITEMS = 30
MAX_QUANTITY_PER_PRODUCT = 50


class CartValidationError(Exception):
    pass


def parse_cart_payload(raw_payload):
    try:
        raw_items = json.loads(raw_payload or "[]")
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CartValidationError("اطلاعات سبد خرید قابل خواندن نیست؛ صفحه را تازه‌سازی کن.") from exc

    if not isinstance(raw_items, list) or not raw_items:
        raise CartValidationError("سبد خرید خالی است.")
    if len(raw_items) > MAX_UNIQUE_CART_ITEMS:
        raise CartValidationError("تعداد کالاهای سبد خرید بیش از حد مجاز است.")

    quantities = {}
    for row in raw_items:
        if not isinstance(row, dict):
            raise CartValidationError("ساختار اطلاعات سبد خرید نامعتبر است.")
        try:
            product_id = int(row.get("id"))
            quantity = int(row.get("quantity", 1))
        except (TypeError, ValueError):
            raise CartValidationError("شناسه یا تعداد یکی از کالاها معتبر نیست.")
        if product_id <= 0 or quantity <= 0 or quantity > MAX_QUANTITY_PER_PRODUCT:
            raise CartValidationError("تعداد درخواستی یکی از کالاها معتبر نیست.")
        quantities[product_id] = quantities.get(product_id, 0) + quantity
        if quantities[product_id] > MAX_QUANTITY_PER_PRODUCT:
            raise CartValidationError("تعداد یک کالا از سقف مجاز بیشتر است.")

    return quantities


def build_validated_cart(raw_payload):
    quantities = parse_cart_payload(raw_payload)
    products = list(
        Product.objects.select_for_update().select_related("category")
        .filter(pk__in=quantities, status="published", category__is_active=True)
        .order_by("pk")
    )
    product_map = {product.pk: product for product in products}
    missing_ids = set(quantities) - set(product_map)
    if missing_ids:
        raise CartValidationError("یک یا چند کالا حذف شده یا دیگر قابل خرید نیستند. سبد را تازه‌سازی کن.")

    currencies = {product.currency_code.upper() for product in products}
    if len(currencies) > 1:
        raise CartValidationError("سبد خرید شامل ارزهای متفاوت است؛ لطفاً با پشتیبانی تماس بگیر.")

    lines = []
    subtotal_raw = Decimal("0")
    subtotal_display = Decimal("0")
    for product_id, quantity in quantities.items():
        product = product_map[product_id]
        if not product.allow_backorder and quantity > product.stock_quantity:
            raise CartValidationError(
                f"موجودی «{product.name}» کافی نیست؛ موجودی فعلی {product.stock_quantity} عدد است."
            )
        unit_price_raw = product.current_price
        line_total_raw = unit_price_raw * quantity
        unit_price_display = to_display_money(unit_price_raw, product.currency_code)
        line_total_display = to_display_money(line_total_raw, product.currency_code)
        subtotal_raw += line_total_raw
        subtotal_display += line_total_display
        lines.append({
            "product": product,
            "quantity": quantity,
            "unit_price_raw": unit_price_raw,
            "line_total_raw": line_total_raw,
            "unit_price_display": unit_price_display,
            "line_total_display": line_total_display,
        })

    return {
        "lines": lines,
        "subtotal_raw": subtotal_raw,
        "subtotal_display": subtotal_display,
        "currency_code": next(iter(currencies)),
    }


def configured_order_creator():
    """Optional adapter for the project's real Order model/app.

    The configured callable must accept keyword arguments:
    request, buyer_data, items, subtotal_raw, currency_code.
    It must create the order and return an order object with `order_number`
    (or a string/number representing the order number).
    """
    creator_path = getattr(settings, "SHOP_ORDER_CREATOR", "")
    if not creator_path:
        return None
    try:
        return import_string(creator_path)
    except (ImportError, AttributeError) as exc:
        raise ImproperlyConfigured("SHOP_ORDER_CREATOR points to an invalid callable.") from exc


def get_order_number(order_result):
    if isinstance(order_result, (str, int)):
        return str(order_result)
    value = getattr(order_result, "order_number", None)
    if value:
        return str(value)
    raise ImproperlyConfigured(
        "SHOP_ORDER_CREATOR must return a string/number or an object with order_number."
    )
