from django.apps import AppConfig


class ShopMemoryConfig(AppConfig):

    default_auto_field = "django.db.models.BigAutoField"

    name = "shop_memory"

    def ready(self):

        from . import signals