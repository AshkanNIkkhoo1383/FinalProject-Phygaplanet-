from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from shop.models import Product

from .manager import ShopMemoryManager


@receiver(post_save, sender=Product)
def sync_product_memory(
    sender,
    instance,
    created,
    **kwargs
):

    product_id = instance.pk

    transaction.on_commit(
        lambda: ShopMemoryManager.sync_product(
            product_id=product_id
        )
    )