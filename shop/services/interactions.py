from django.db.models import F

from ..models import Product, ProductInteraction


COUNTER_FIELDS = {
    "view": "view_count",
    "wishlist": "wishlist_count",
    "cart": "cart_add_count",
    "purchase": "purchase_count",
}


def ensure_session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key or ""


def record_product_interaction(
    request,
    product: Product,
    *,
    event_type: str,
    source: str = "direct",
    quantity: int = 1,
    search_query: str = "",
    metadata=None,
):
    """Persist an event and update the matching aggregate counter atomically at DB level."""
    allowed_events = {choice[0] for choice in ProductInteraction._meta.get_field("event_type").choices}
    allowed_sources = {choice[0] for choice in ProductInteraction._meta.get_field("source").choices}
    if event_type not in allowed_events:
        raise ValueError("Unsupported interaction event")
    if source not in allowed_sources:
        source = "direct"

    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    event = ProductInteraction.objects.create(
        user=user,
        product=product,
        event_type=event_type,
        source=source,
        session_key=ensure_session_key(request),
        search_query=(search_query or "")[:255],
        quantity=max(1, int(quantity or 1)),
        price_at_event=product.current_price,
        metadata=metadata or {},
    )

    counter_field = COUNTER_FIELDS.get(event_type)
    if counter_field:
        Product.objects.filter(pk=product.pk).update(**{counter_field: F(counter_field) + 1})
    return event
