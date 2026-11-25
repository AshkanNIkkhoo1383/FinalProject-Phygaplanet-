from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db.models import Case, DecimalField, F, When
from django.urls import reverse

from ..models import Product


UI_TYPE_MAP = {
    "album": ("album", "vinyl"),
    "poster": ("poster",),
    "mug": ("mug",),
    "memorabilia": ("tshirt", "hoodie", "keychain", "sticker", "tote_bag", "collectible", "other"),
}

TYPE_LABELS = {
    "album": "آلبوم فیزیکی",
    "vinyl": "صفحه وینیل",
    "poster": "پوستر و چاپ",
    "mug": "ماگ و اکسسوری",
    "tshirt": "پوشاک",
    "hoodie": "پوشاک",
    "keychain": "یادگاری‌ها",
    "sticker": "یادگاری‌ها",
    "tote_bag": "یادگاری‌ها",
    "collectible": "کلکسیونی",
    "other": "یادگاری موسیقی",
}

TYPE_VISUALS = {
    "album": ("album", "▣"),
    "vinyl": ("album", "♫"),
    "poster": ("poster", "▤"),
    "mug": ("mug", "☕"),
}


def get_price_divisor(currency_code: str) -> Decimal:
    """Return display divisor. IRR is divided by 10 because UI prices are shown in toman.

    Set SHOP_IRR_TO_TOMAN_DIVISOR=1 if the database already stores toman values.
    """
    if (currency_code or "").upper() == "IRR":
        try:
            divisor = Decimal(str(getattr(settings, "SHOP_IRR_TO_TOMAN_DIVISOR", 10)))
        except (InvalidOperation, TypeError):
            divisor = Decimal("10")
        return divisor if divisor > 0 else Decimal("10")
    return Decimal("1")


def to_display_money(amount, currency_code="IRR") -> Decimal:
    return Decimal(amount or 0) / get_price_divisor(currency_code)


def primary_image(product):
    images = list(product.images.all())
    return next((image for image in images if image.is_primary), images[0] if images else None)


def product_to_ui(product, *, featured=False, source="direct"):
    image = primary_image(product)
    try:
        image_url = image.image.url if image and image.image else ""
    except (ValueError, AttributeError):
        image_url = ""

    visual_key, emoji = TYPE_VISUALS.get(product.product_type, ("memorabilia", "✦"))
    sale_active = product.sale_price is not None and product.sale_price < product.price
    current_price = product.current_price
    ai_summary = product.ai_summary if product.ai_status == "processed" else ""
    display_price = to_display_money(current_price, product.currency_code)
    old_price = to_display_money(product.price, product.currency_code) if sale_active else None

    detail_url = reverse("shop:product_detail", kwargs={"slug": product.slug})
    if source in {"direct", "search", "recommendation", "category", "external"} and source != "direct":
        detail_url = f"{detail_url}?source={source}"

    return {
        "id": product.pk,
        "name": product.name,
        "slug": product.slug,
        "detail_url": detail_url,
        "image_url": image_url,
        "emoji": emoji,
        "visual_key": visual_key,
        "category_slug": visual_key if visual_key in UI_TYPE_MAP else "memorabilia",
        "category_name": product.category.name if product.category_id else TYPE_LABELS.get(product.product_type, "یادگاری موسیقی"),
        "price": display_price,
        "old_price": old_price,
        "stock": product.stock_quantity,
        "badge": "تخفیف ویژه" if sale_active else ("انتخاب مایک" if featured else ""),
        "badge_kind": "yellow" if sale_active else "lime",
        "short_description": product.short_description or ai_summary[:220],
        "sku": product.sku,
        "artist_name": product.artist_name,
        "album_name": product.album_name,
        "description": product.description or ai_summary,
        "specifications": product.specifications or {},
        "authenticity": product.get_authenticity_display(),
        "edition": product.edition,
        "release_year": product.release_year,
        "average_rating": product.average_rating,
        "rating_count": product.rating_count,
        "is_in_stock": product.is_in_stock,
        "available_stock_flag": 1 if product.is_in_stock else 0,
        "purchase_limit": 50 if product.allow_backorder else product.stock_quantity,
    }


def published_products():
    return (
        Product.objects.filter(status="published", category__is_active=True)
        .select_related("category")
        .prefetch_related("images")
        .annotate(
            effective_price=Case(
                When(sale_price__lt=F("price"), then=F("sale_price")),
                default=F("price"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )
