"""Template contract for connecting the shop checkout to the project's Order app.

1. Implement this function in the app that owns the real Order/OrderItem models.
2. Validate or reserve stock inside the same transaction.
3. Persist monetary values in the same currency unit as Product.price.
4. Return the created order, which must expose `order_number`.
5. Set SHOP_ORDER_CREATOR to this function's dotted import path in settings.py.

This file intentionally does not import or invent an Order model because none was
included in the Product models supplied for this implementation.
"""


def create_order_from_shop_checkout(*, request, buyer_data, items, subtotal_raw, currency_code):
    # Example shape of `items`:
    # [{"product": Product, "product_id": 1, "quantity": 2,
    #   "unit_price": Decimal(...), "line_total": Decimal(...),
    #   "currency_code": "IRR"}, ...]
    # TODO: create Order and OrderItem rows using your actual models.
    raise NotImplementedError("Connect this adapter to your actual Order and OrderItem models.")
