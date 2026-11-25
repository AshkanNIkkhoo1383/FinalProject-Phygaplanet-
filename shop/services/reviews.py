from decimal import Decimal

from django.db.models import Avg, Count

from ..models import Product, ProductReview


def refresh_product_rating(product_id):
    """Update cached Product rating using approved reviews only."""
    stats = ProductReview.objects.filter(
        product_id=product_id,
        status="approved",
    ).aggregate(average=Avg("rating"), total=Count("id"))
    average = Decimal(str(stats["average"] or 0)).quantize(Decimal("0.01"))
    Product.objects.filter(pk=product_id).update(
        average_rating=average,
        rating_count=stats["total"],
    )
