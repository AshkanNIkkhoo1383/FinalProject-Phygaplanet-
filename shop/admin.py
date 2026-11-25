from django.contrib import admin

from .models import Category, Product, ProductImage, ProductInteraction, ProductReview
from .services.reviews import refresh_product_rating


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "product_type", "category", "status", "price", "sale_price",
        "stock_quantity", "popularity_score", "ai_status", "updated_at",
    )
    list_filter = ("status", "product_type", "category", "authenticity", "ai_status")
    search_fields = ("name", "sku", "artist_name", "album_name", "collection_name")
    list_select_related = ("category", "created_by")
    readonly_fields = (
        "view_count", "wishlist_count", "cart_add_count", "purchase_count",
        "average_rating", "rating_count", "popularity_score", "created_at", "updated_at",
        "ai_processed_at",
    )
    inlines = (ProductImageInline,)
    save_on_top = True


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "status", "created_at")
    list_filter = ("status", "rating", "created_at")
    search_fields = ("product__name", "user__username", "title", "comment")
    list_select_related = ("product", "user")
    actions = ("approve_reviews", "reject_reviews")

    def save_model(self, request, obj, form, change):
        old_product_id = None
        if change:
            old_product_id = ProductReview.objects.filter(pk=obj.pk).values_list("product_id", flat=True).first()
        super().save_model(request, obj, form, change)
        if old_product_id:
            refresh_product_rating(old_product_id)
        refresh_product_rating(obj.product_id)

    def delete_model(self, request, obj):
        product_id = obj.product_id
        super().delete_model(request, obj)
        refresh_product_rating(product_id)

    def delete_queryset(self, request, queryset):
        product_ids = set(queryset.values_list("product_id", flat=True))
        super().delete_queryset(request, queryset)
        for product_id in product_ids:
            refresh_product_rating(product_id)

    @admin.action(description="تأیید نظرهای انتخاب‌شده")
    def approve_reviews(self, request, queryset):
        product_ids = set(queryset.values_list("product_id", flat=True))
        queryset.update(status="approved")
        for product_id in product_ids:
            refresh_product_rating(product_id)

    @admin.action(description="رد نظرهای انتخاب‌شده")
    def reject_reviews(self, request, queryset):
        product_ids = set(queryset.values_list("product_id", flat=True))
        queryset.update(status="rejected")
        for product_id in product_ids:
            refresh_product_rating(product_id)


@admin.register(ProductInteraction)
class ProductInteractionAdmin(admin.ModelAdmin):
    list_display = ("event_type", "product", "user", "source", "quantity", "created_at")
    list_filter = ("event_type", "source", "created_at")
    search_fields = ("product__name", "user__username", "search_query", "session_key")
    list_select_related = ("product", "user")
    readonly_fields = tuple(field.name for field in ProductInteraction._meta.fields)

    def has_add_permission(self, request):
        return False
