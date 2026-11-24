
import numpy as np

from decimal import Decimal, InvalidOperation

from django.db.models import Q, DecimalField
from django.db.models.functions import Coalesce

from shop_memory.models import (
    ProductMemory,
    KnowledgeChunk,
)

from shop_memory.manager import ShopMemoryManager


class ShopRetriever:

    MIN_SIMILARITY = 0.20
    MAX_CANDIDATES = 3000

    # ==========================================
    # Similarity
    # ==========================================

    @staticmethod
    def similarity(query_vector, stored_vector):

        if not isinstance(stored_vector, list):
            return 0.0

        if not stored_vector:
            return 0.0

        candidate = np.asarray(
            stored_vector,
            dtype=np.float32
        )

        if candidate.shape != query_vector.shape:
            return 0.0

        return float(
            np.dot(query_vector, candidate)
        )

    # ==========================================
    # Product Retrieval
    # ==========================================

    @classmethod
    def search_products(
        cls,
        query_vector,
        filters=None,
        top_k=3
    ):

        filters = filters or {}

        queryset = (
            ProductMemory.objects
            .filter(
                index_status="ready",
                product__status="published"
            )
            .select_related(
                "product",
                "product__category"
            )
        )

        # --------------------------------------
        # Exact filters
        # --------------------------------------

        artist = filters.get("artist_name")

        if artist:
            queryset = queryset.filter(
                product__artist_name__icontains=artist
            )

        product_type = filters.get("product_type")

        if product_type:
            queryset = queryset.filter(
                product__product_type=product_type
            )

        category = filters.get("category")

        if category:
            queryset = queryset.filter(
                product__category__name__icontains=category
            )

        currency = filters.get("currency_code")

        if currency:
            queryset = queryset.filter(
                product__currency_code=currency
            )

        # Sale price takes precedence because the Product
        # model already validates that it is lower than price.
        if (
            "max_price" in filters
            or "min_price" in filters
        ):

            if not currency:
                raise ValueError(
                    "A currency_code is required "
                    "when filtering products by price."
                )

            queryset = queryset.annotate(
                live_price=Coalesce(
                    "product__sale_price",
                    "product__price",
                    output_field=DecimalField(
                        max_digits=14,
                        decimal_places=2
                    )
                )
            )

            try:

                if "max_price" in filters:

                    max_price = Decimal(
                        str(filters["max_price"])
                    )

                    queryset = queryset.filter(
                        live_price__lte=max_price
                    )

                if "min_price" in filters:

                    min_price = Decimal(
                        str(filters["min_price"])
                    )

                    queryset = queryset.filter(
                        live_price__gte=min_price
                    )

            except InvalidOperation as exc:

                raise ValueError(
                    "Invalid price filter."
                ) from exc

        if filters.get("in_stock") is True:

            queryset = queryset.filter(
                Q(product__stock_quantity__gt=0)
                | Q(product__allow_backorder=True)
            )

        candidates = list(
            queryset[:cls.MAX_CANDIDATES]
        )

        ranked = []

        for memory in candidates:

            score = cls.similarity(
                query_vector,
                memory.embedding
            )

            if score >= cls.MIN_SIMILARITY:

                ranked.append(
                    (score, memory)
                )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True
        )

        selected = ranked[:top_k]

        now_results = [
            memory for score, memory in selected
        ]

        # Record retrieval activity.
        for memory in now_results:

            ShopMemoryManager.record_product_access(
                memory.pk
            )

        return now_results

    # ==========================================
    # Knowledge Retrieval
    # ==========================================

    @classmethod
    def search_knowledge(
        cls,
        query_vector,
        top_k=4
    ):

        chunks = list(
            KnowledgeChunk.objects.filter(
                is_embedded=True,
                document__status="published"
            ).select_related(
                "document"
            )[:cls.MAX_CANDIDATES]
        )

        ranked = []

        for chunk in chunks:

            score = cls.similarity(
                query_vector,
                chunk.embedding
            )

            if score >= cls.MIN_SIMILARITY:

                ranked.append(
                    (score, chunk)
                )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True
        )

        selected = [
            chunk for score, chunk in ranked[:top_k]
        ]

        for chunk in selected:

            ShopMemoryManager.record_knowledge_access(
                chunk.pk
            )

        return selected
