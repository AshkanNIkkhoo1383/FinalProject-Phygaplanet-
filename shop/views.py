import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import CheckoutForm, ProductReviewForm
from .models import Product, ProductInteraction, ProductReview
from .services.catalog import UI_TYPE_MAP, product_to_ui, published_products
from .services.checkout import (
    CartValidationError,
    build_validated_cart,
    configured_order_creator,
    get_order_number,
)
from .services.interactions import record_product_interaction
from .services.reviews import refresh_product_rating


PAGE_SIZE = 12


def _source_from_request(request):
    allowed = {choice[0] for choice in ProductInteraction._meta.get_field("source").choices}
    source = request.GET.get("source", "direct")
    return source if source in allowed else "direct"


def _detail_context(product, *, review_form=None):
    related_qs = (
        published_products()
        .filter(Q(category=product.category) | Q(product_type=product.product_type))
        .exclude(pk=product.pk)
        .order_by("-popularity_score", "-purchase_count", "-created_at")
        .distinct()[:4]
    )
    reviews = (
        ProductReview.objects.filter(product=product, status="approved")
        .select_related("user")[:8]
    )
    return {
        "product": product_to_ui(product),
        "related_products": [product_to_ui(item, source="recommendation") for item in related_qs],
        "reviews": reviews,
        "review_form": review_form or ProductReviewForm(),
        "can_review": True,
    }


@require_GET
def shop_home(request):
    """Shop landing page. Mike's picks are currently popularity-based, not LLM output."""
    base = published_products()
    featured = base.order_by("-popularity_score", "-purchase_count", "-view_count", "-created_at")[:4]
    newest = base.order_by("-created_at")[:4]
    return render(request, "shop_ui/home.html", {
        "featured_products": [product_to_ui(item, featured=True, source="recommendation") for item in featured],
        "new_products": [product_to_ui(item, source="category") for item in newest],
    })


@require_GET
def product_list(request):
    queryset = published_products()

    query = (request.GET.get("q") or "").strip()[:120]
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(artist_name__icontains=query)
            | Q(album_name__icontains=query)
            | Q(collection_name__icontains=query)
            | Q(short_description__icontains=query)
            | Q(description__icontains=query)
            | Q(ai_status="processed", ai_search_text__icontains=query)
        )

    selected_category = request.GET.get("type", "all")
    if selected_category in UI_TYPE_MAP:
        queryset = queryset.filter(product_type__in=UI_TYPE_MAP[selected_category])
    else:
        selected_category = "all"

    if request.GET.get("available") in ("1", "true", "yes"):
        queryset = queryset.filter(Q(stock_quantity__gt=0) | Q(allow_backorder=True))

    # max_price is understood as toman in the UI; Product.price is stored in the currency
    # defined by Product.currency_code (IRR is divided by 10 for toman display by default).
    max_price = request.GET.get("max_price")
    if max_price:
        try:
            from .services.catalog import get_price_divisor
            divisor = get_price_divisor("IRR")
            raw_max = Decimal(max_price) * divisor
            queryset = queryset.filter(effective_price__lte=raw_max)
        except (InvalidOperation, TypeError, ValueError):
            pass

    sort = request.GET.get("sort", "recommended")
    if sort == "price-asc":
        queryset = queryset.order_by("effective_price", "name")
    elif sort == "price-desc":
        queryset = queryset.order_by("-effective_price", "name")
    elif sort == "name":
        queryset = queryset.order_by("name")
    else:
        queryset = queryset.order_by("-popularity_score", "-purchase_count", "-created_at")

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    list_source = "search" if query else ("category" if selected_category != "all" else "direct")
    products = [product_to_ui(item, source=list_source) for item in page_obj.object_list]
    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(request, "shop_ui/product_list.html", {
        "products": products,
        "page_obj": page_obj,
        "result_count": paginator.count,
        "selected_category": selected_category,
        "search_query": query,
        "selected_sort": sort,
        "querystring": query_params.urlencode(),
    })


@require_GET
def product_detail(request, slug):
    product = get_object_or_404(published_products(), slug=slug)
    record_product_interaction(
        request,
        product,
        event_type="view",
        source=_source_from_request(request),
        search_query=request.GET.get("q", ""),
    )
    return render(request, "shop_ui/product_detail.html", _detail_context(product))


@require_GET
def cart_view(request):
    # The visual UI currently stores cart ids/quantities in localStorage.
    # Checkout posts only ids/quantities; server-side prices and stock are revalidated.
    return render(request, "shop_ui/cart.html")


@require_http_methods(["GET", "POST"])
@transaction.atomic
def checkout_view(request):
    if request.method == "GET":
        return render(request, "shop_ui/checkout.html", {
            "form": CheckoutForm(),
            "checkout_submit_url": reverse("shop:checkout"),
        })

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return render(request, "shop_ui/checkout.html", {
            "form": form,
            "checkout_submit_url": reverse("shop:checkout"),
        }, status=400)

    try:
        # Reload all product details from the database; never trust prices from localStorage.
        cart = build_validated_cart(form.cleaned_data["cart_payload"])
    except CartValidationError as exc:
        form.add_error(None, str(exc))
        return render(request, "shop_ui/checkout.html", {
            "form": form,
            "checkout_submit_url": reverse("shop:checkout"),
        }, status=400)

    creator = configured_order_creator()
    buyer_data = {
        key: value for key, value in form.cleaned_data.items()
        if key not in {"cart_payload"}
    }

    if creator is None:
        # There is no Order model in the models supplied so far. Show a validated
        # server-side preview, but do not pretend that an order has been created.
        return render(request, "shop_ui/checkout_review.html", {
            "buyer_data": buyer_data,
            "cart": cart,
            "order_creation_enabled": False,
        })

    order_items = [
        {
            "product": line["product"],
            "product_id": line["product"].pk,
            "quantity": line["quantity"],
            "unit_price": line["unit_price_raw"],
            "line_total": line["line_total_raw"],
            "currency_code": line["product"].currency_code,
        }
        for line in cart["lines"]
    ]
    with transaction.atomic():
        order_result = creator(
            request=request,
            buyer_data=buyer_data,
            items=order_items,
            subtotal_raw=cart["subtotal_raw"],
            currency_code=cart["currency_code"],
        )
        order_number = get_order_number(order_result)

    return render(request, "shop_ui/order_success.html", {
        "order_number": order_number,
    })


@login_required
@require_POST
def submit_review(request, slug):
    product = get_object_or_404(Product, slug=slug, status="published", category__is_active=True)
    form = ProductReviewForm(request.POST)
    if not form.is_valid():
        context = _detail_context(product, review_form=form)
        return render(request, "shop_ui/product_detail.html", context, status=400)

    ProductReview.objects.update_or_create(
        user=request.user,
        product=product,
        defaults={
            "rating": form.cleaned_data["rating"],
            "title": form.cleaned_data["title"],
            "comment": form.cleaned_data["comment"],
            "status": "pending",
        },
    )
    refresh_product_rating(product.pk)
    messages.success(request, "نظر تو ثبت شد و پس از بررسی نمایش داده می‌شود.")
    return redirect(f"{reverse('shop:product_detail', kwargs={'slug': slug})}#reviews")


@require_POST
def track_cart_interaction(request):
    """Record an add-to-cart event sent by the shop JavaScript."""
    try:
        payload = json.loads(request.body.decode("utf-8"))
        product_id = int(payload.get("product_id"))
        quantity = int(payload.get("quantity", 1))
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, TypeError, ValueError):
        return HttpResponseBadRequest("Invalid interaction payload")

    if product_id <= 0 or quantity < 1 or quantity > 50:
        return HttpResponseBadRequest("Invalid product or quantity")

    product = get_object_or_404(Product, pk=product_id, status="published", category__is_active=True)
    record_product_interaction(
        request,
        product,
        event_type="cart",
        source="direct",
        quantity=quantity,
        metadata={"via": "shop_ui"},
    )
    return JsonResponse({"ok": True})
