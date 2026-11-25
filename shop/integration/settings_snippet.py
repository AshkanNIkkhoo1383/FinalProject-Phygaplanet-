# Add the following entries to your existing settings.py (do not duplicate them).

# App should already be installed if the current shop/models.py is active.
# INSTALLED_APPS += ["shop"]

# Your Product model defaults currency_code to IRR, while the shop UI labels
# values as toman. Default 10 means rial -> toman. Use 1 if database prices
# are already stored in toman.
SHOP_IRR_TO_TOMAN_DIVISOR = 10

# Leave empty until you share/implement your real Order model integration.
# Expected callable signature:
# creator(request, buyer_data, items, subtotal_raw, currency_code)
# SHOP_ORDER_CREATOR = "orders.shop_adapter.create_order_from_shop_checkout"

# Existing media settings should be retained. Example if they are not set yet:
# MEDIA_URL = "/media/"
# MEDIA_ROOT = BASE_DIR / "media"
