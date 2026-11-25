from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.shop_home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("products/<slug:slug>/reviews/", views.submit_review, name="submit_review"),
    path("cart/", views.cart_view, name="cart"),
    path("checkout/", views.checkout_view, name="checkout"),
    path("interactions/cart/", views.track_cart_interaction, name="track_cart"),
]
