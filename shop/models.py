
import uuid

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator,
)
from django.utils.text import slugify


# =====================================================
# Constants
# =====================================================

PRODUCT_TYPES = [
    ("album", "Physical Album"),
    ("poster", "Poster"),
    ("mug", "Mug"),
    ("tshirt", "T-Shirt"),
    ("hoodie", "Hoodie"),
    ("keychain", "Keychain"),
    ("sticker", "Sticker"),
    ("vinyl", "Vinyl Record"),
    ("tote_bag", "Tote Bag"),
    ("collectible", "Collectible"),
    ("other", "Other"),
]

PRODUCT_STATUS = [
    ("draft", "Draft"),
    ("published", "Published"),
    ("archived", "Archived"),
]

AUTHENTICITY_TYPES = [
    ("official", "Official Merchandise"),
    ("licensed", "Licensed Merchandise"),
    ("fan_made", "Fan Made"),
    ("independent", "Independent Artist"),
    ("unknown", "Unknown"),
]

PRICE_SEGMENTS = [
    ("budget", "Budget"),
    ("mid_range", "Mid Range"),
    ("premium", "Premium"),
]

AI_STATUS = [
    ("pending", "Pending"),
    ("processed", "Processed"),
    ("failed", "Failed"),
]

INTERACTION_TYPES = [
    ("view", "View"),
    ("click", "Click"),
    ("wishlist", "Wishlist"),
    ("cart", "Add to Cart"),
    ("purchase", "Purchase"),
    ("compare", "Compare"),
    ("share", "Share"),
]

INTERACTION_SOURCES = [
    ("direct", "Direct"),
    ("search", "Search"),
    ("recommendation", "Recommendation"),
    ("category", "Category"),
    ("external", "External"),
]

REVIEW_STATUS = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]

SCORE_VALIDATORS = [
    MinValueValidator(Decimal("0")),
    MaxValueValidator(Decimal("1")),
]


def generate_slug(value):
    """
    Generate a readable and unique slug.
    """

    base = slugify(value)[:140] or "product"

    return f"{base}-{uuid.uuid4().hex[:8]}"


# =====================================================
# Category
# =====================================================

class Category(models.Model):

    name = models.CharField(
        max_length=120,
        unique=True
    )

    slug = models.SlugField(
        max_length=180,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children"
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = generate_slug(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]


# =====================================================
# Product
# =====================================================

class Product(models.Model):

    # -------------------------------------------------
    # 1. Basic Information
    # -------------------------------------------------

    name = models.CharField(
        max_length=200,
        verbose_name="Product Name"
    )

    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True
    )

    sku = models.CharField(
        max_length=64,
        blank=True,
        default=""
    )

    product_type = models.CharField(
        max_length=30,
        choices=PRODUCT_TYPES,
        default="other"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    status = models.CharField(
        max_length=20,
        choices=PRODUCT_STATUS,
        default="draft"
    )

    # -------------------------------------------------
    # 2. Music Related Information
    # -------------------------------------------------

    artist_name = models.CharField(
        max_length=200,
        blank=True
    )

    album_name = models.CharField(
        max_length=200,
        blank=True
    )

    collection_name = models.CharField(
        max_length=200,
        blank=True
    )

    authenticity = models.CharField(
        max_length=20,
        choices=AUTHENTICITY_TYPES,
        default="unknown"
    )

    edition = models.CharField(
        max_length=120,
        blank=True
    )

    release_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    # -------------------------------------------------
    # 3. Product Description
    # -------------------------------------------------

    short_description = models.CharField(
        max_length=300,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    tags = models.JSONField(
        default=list,
        blank=True
    )

    music_genres = models.JSONField(
        default=list,
        blank=True
    )

    target_audience = models.JSONField(
        default=list,
        blank=True
    )

    # Flexible specifications:
    # Material, color, size, dimensions, format, etc.

    specifications = models.JSONField(
        default=dict,
        blank=True
    )

    # -------------------------------------------------
    # 4. Pricing
    # -------------------------------------------------

    currency_code = models.CharField(
        max_length=3,
        default="IRR"
    )

    price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0"))
        ]
    )

    sale_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0"))
        ]
    )

    cost_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0"))
        ]
    )

    # -------------------------------------------------
    # 5. Inventory
    # -------------------------------------------------

    stock_quantity = models.PositiveIntegerField(
        default=0
    )

    low_stock_threshold = models.PositiveIntegerField(
        default=5
    )

    allow_backorder = models.BooleanField(
        default=False
    )

    # -------------------------------------------------
    # 6. Data Mining Features
    # -------------------------------------------------

    view_count = models.PositiveBigIntegerField(
        default=0
    )

    wishlist_count = models.PositiveBigIntegerField(
        default=0
    )

    cart_add_count = models.PositiveBigIntegerField(
        default=0
    )

    purchase_count = models.PositiveBigIntegerField(
        default=0
    )

    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("5")),
        ]
    )

    rating_count = models.PositiveIntegerField(
        default=0
    )

    popularity_score = models.DecimalField(
        max_digits=7,
        decimal_places=5,
        default=0,
        validators=SCORE_VALIDATORS
    )

    price_segment = models.CharField(
        max_length=20,
        choices=PRICE_SEGMENTS,
        blank=True
    )

    feature_vector = models.JSONField(
        default=dict,
        blank=True
    )

    cluster_label = models.CharField(
        max_length=100,
        blank=True
    )

    # -------------------------------------------------
    # 7. LLM Integration
    # -------------------------------------------------

    ai_summary = models.TextField(
        blank=True
    )

    ai_search_text = models.TextField(
        blank=True
    )

    ai_keywords = models.JSONField(
        default=list,
        blank=True
    )

    ai_extracted_attributes = models.JSONField(
        default=dict,
        blank=True
    )

    ai_price_analysis = models.JSONField(
        default=dict,
        blank=True
    )

    ai_embedding = models.JSONField(
        default=list,
        blank=True
    )

    ai_status = models.CharField(
        max_length=20,
        choices=AI_STATUS,
        default="pending"
    )

    ai_model_name = models.CharField(
        max_length=120,
        blank=True
    )

    embedding_model = models.CharField(
        max_length=120,
        blank=True
    )

    ai_processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # -------------------------------------------------
    # 8. Ownership and Timestamps
    # -------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_shop_products"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # -------------------------------------------------
    # 9. Properties
    # -------------------------------------------------

    @property
    def current_price(self):

        if (
            self.sale_price is not None
            and self.sale_price < self.price
        ):
            return self.sale_price

        return self.price

    @property
    def is_in_stock(self):

        return (
            self.stock_quantity > 0
            or self.allow_backorder
        )

    # -------------------------------------------------
    # 10. Methods
    # -------------------------------------------------

    def save(self, *args, **kwargs):

        if not self.slug:
            self.slug = generate_slug(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:

        verbose_name = "Product"
        verbose_name_plural = "Products"

        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status", "category"]
            ),

            models.Index(
                fields=["product_type", "status"]
            ),

            models.Index(
                fields=["price"]
            ),

            models.Index(
                fields=["created_at"]
            ),
        ]

        constraints = [

            models.UniqueConstraint(
                fields=["sku"],
                condition=~Q(sku=""),
                name="unique_nonempty_product_sku"
            ),

            models.CheckConstraint(
                condition=(
                    Q(sale_price__isnull=True)
                    | Q(sale_price__lt=F("price"))
                ),
                name="sale_price_lower_than_price"
            ),
        ]


# =====================================================
# Product Images
# =====================================================

class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(
        upload_to="shop/products/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "jpg",
                    "jpeg",
                    "png",
                    "webp"
                ]
            )
        ]
    )

    alt_text = models.CharField(
        max_length=200,
        blank=True
    )

    is_primary = models.BooleanField(
        default=False
    )

    sort_order = models.PositiveSmallIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Image - {self.product.name}"

    class Meta:

        ordering = ["sort_order", "created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(is_primary=True),
                name="one_primary_image_per_product"
            ),
        ]


# =====================================================
# Product Interaction
# =====================================================

class ProductInteraction(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_interactions"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="interactions"
    )

    event_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES
    )

    source = models.CharField(
        max_length=20,
        choices=INTERACTION_SOURCES,
        default="direct"
    )

    session_key = models.CharField(
        max_length=64,
        blank=True
    )

    search_query = models.CharField(
        max_length=255,
        blank=True
    )

    quantity = models.PositiveIntegerField(
        default=1
    )

    dwell_time_seconds = models.PositiveIntegerField(
        default=0
    )

    price_at_event = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.event_type} - "
            f"{self.product.name}"
        )

    class Meta:

        ordering = ["-created_at"]

        indexes = [

            models.Index(
                fields=[
                    "product",
                    "event_type",
                    "created_at"
                ]
            ),

            models.Index(
                fields=[
                    "user",
                    "created_at"
                ]
            ),

            models.Index(
                fields=[
                    "event_type",
                    "created_at"
                ]
            ),
        ]


# =====================================================
# Product Review
# =====================================================

class ProductReview(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shop_reviews"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews"
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )

    title = models.CharField(
        max_length=150,
        blank=True
    )

    comment = models.TextField(
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return (
            f"{self.product.name} - "
            f"{self.rating}/5"
        )

    class Meta:

        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="one_review_per_user_product"
            ),
        ]

        indexes = [
            models.Index(
                fields=["product", "status"]
            )
        ]
