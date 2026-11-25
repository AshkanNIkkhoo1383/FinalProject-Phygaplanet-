from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from shop.models import Category, Product


class ShopPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="آلبوم فیزیکی")
        cls.product = Product.objects.create(
            name="Test Album",
            product_type="album",
            category=cls.category,
            status="published",
            price=Decimal("1200000"),
            currency_code="IRR",
            stock_quantity=4,
        )

    def test_shop_home_renders(self):
        response = self.client.get(reverse("shop:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "فروشگاه")

    def test_product_detail_records_view_interaction(self):
        response = self.client.get(reverse("shop:product_detail", kwargs={"slug": self.product.slug}))
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.view_count, 1)

    def test_cart_interaction_records_event(self):
        response = self.client.post(
            reverse("shop:track_cart"),
            data='{"product_id": %s, "quantity": 2}' % self.product.pk,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.cart_add_count, 1)

    def test_draft_products_are_not_public(self):
        draft = Product.objects.create(
            name="Draft Album",
            product_type="album",
            category=self.category,
            status="draft",
            price=Decimal("500000"),
        )
        response = self.client.get(reverse("shop:product_detail", kwargs={"slug": draft.slug}))
        self.assertEqual(response.status_code, 404)
