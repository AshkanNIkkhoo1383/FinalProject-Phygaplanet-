# Add this include to the project's root config/urls.py.
# Keep any existing URL patterns; do not replace the entire urlpatterns list.

from django.urls import include, path

urlpatterns += [
    path("shop/", include("shop.urls")),
]
