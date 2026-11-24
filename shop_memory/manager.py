
import hashlib
import json

from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from shop.models import Product

from .models import (
    ProductMemory,
    KnowledgeDocument,
    KnowledgeChunk,
    RequestedProduct,
    ProductRequestEvent,
)


class ShopMemoryManager:

    # ==========================================
    # Configuration
    # ==========================================

    CACHE_TIMEOUT = 300

    CHUNK_SIZE = 180
    CHUNK_OVERLAP = 30

    INACTIVE_DAYS = 90

    FREQUENT = "frequent"
    NORMAL = "normal"
    LOW = "low"

    # ==========================================
    # 1. Admin Message Handler
    # ==========================================

    @classmethod
    def process_admin_message(cls, payload):

        if not isinstance(payload, dict):
            raise ValidationError(
                "Admin message must be a dictionary."
            )

        action = payload.get("action")

        if action == "sync_product":

            return cls.sync_product(
                product_id=payload.get("product_id"),
                admin_importance=payload.get(
                    "admin_importance"
                ),
                is_protected=payload.get(
                    "is_protected"
                )
            )

        elif action == "add_knowledge":

            return cls.add_knowledge(payload)

        elif action == "update_knowledge":

            return cls.update_knowledge(payload)

        raise ValidationError(
            "Unknown memory action."
        )

    # ==========================================
    # 2. Product Memory Synchronization
    # ==========================================

    @classmethod
    def sync_product(
        cls,
        product_id,
        admin_importance=None,
        is_protected=None
    ):

        product = (
            Product.objects
            .select_related("category")
            .get(pk=product_id)
        )

        category_name = (
            product.category.name
            if product.category_id
            else ""
        )

        product_data = {
            "name": product.name,
            "product_type": product.product_type,
            "category": category_name,
            "artist": product.artist_name,
            "album": product.album_name,
            "collection": product.collection_name,
            "short_description": product.short_description,
            "description": product.description,
            "tags": product.tags,
            "genres": product.music_genres,
            "target_audience": product.target_audience,
            "specifications": product.specifications,
        }

        searchable_text = json.dumps(
            product_data,
            ensure_ascii=False,
            default=str
        )

        content_hash = hashlib.sha256(
            searchable_text.encode("utf-8")
        ).hexdigest()

        memory, created = (
            ProductMemory.objects.get_or_create(
                product=product
            )
        )

        changed = (
            created
            or memory.content_hash != content_hash
        )

        if changed:

            memory.searchable_text = searchable_text

            memory.summary = (
                product.short_description
                or product.description[:400]
            )

            keywords = [
                product.artist_name,
                product.album_name,
                product.product_type,
            ]

            keywords.extend(product.tags or [])
            keywords.extend(product.music_genres or [])

            memory.keywords = list(dict.fromkeys(
                item for item in keywords
                if isinstance(item, str) and item.strip()
            ))

            memory.extracted_attributes = (
                product.specifications or {}
            )

            # Old embedding is no longer valid.
            memory.embedding = []

            memory.embedding_model = ""

            memory.index_status = "pending"

            memory.content_hash = content_hash

        if admin_importance is not None:

            if not 1 <= int(admin_importance) <= 5:
                raise ValidationError(
                    "admin_importance must be between 1 and 5."
                )

            memory.admin_importance = int(
                admin_importance
            )

        if is_protected is not None:
            memory.is_protected = bool(is_protected)

        cls._apply_importance(memory)

        memory.save()

        cache.delete(
            f"shop_memory:product:{product.pk}"
        )

        return memory

    # ==========================================
    # 3. Add Knowledge From Admin
    # ==========================================

    @classmethod
    @transaction.atomic
    def add_knowledge(cls, payload):

        knowledge_type = payload.get(
            "knowledge_type"
        )

        title = payload.get("title", "").strip()

        if not title:
            raise ValidationError(
                "Knowledge title is required."
            )

        question = payload.get("question", "")
        answer = payload.get("answer", "")
        content = payload.get("content", "")

        if knowledge_type == "faq":

            if not question.strip() or not answer.strip():
                raise ValidationError(
                    "FAQ requires both question and answer."
                )

        elif not content.strip():

            raise ValidationError(
                "Knowledge content is required."
            )

        document = KnowledgeDocument(
            knowledge_type=knowledge_type,
            title=title,
            question=question,
            answer=answer,
            content=content,
            tags=payload.get("tags", []),
            source=payload.get("source", ""),
            priority=payload.get("priority", 1),
            admin_importance=payload.get(
                "admin_importance", 3
            ),
            status=payload.get("status", "published"),
            is_protected=payload.get(
                "is_protected", True
            )
        )

        document.full_clean()
        document.save()

        cls.rebuild_chunks(document)

        cls._apply_importance(document)
        document.save()

        return document

    # ==========================================
    # 4. Update Existing Knowledge
    # ==========================================

    @classmethod
    @transaction.atomic
    def update_knowledge(cls, payload):

        document = KnowledgeDocument.objects.get(
            pk=payload.get("document_id")
        )

        allowed_fields = [
            "title",
            "question",
            "answer",
            "content",
            "tags",
            "source",
            "priority",
            "admin_importance",
            "status",
            "is_protected",
        ]

        for field in allowed_fields:

            if field in payload:
                setattr(
                    document,
                    field,
                    payload[field]
                )

        document.full_clean()
        document.save()

        # Rebuild chunks because source text may have changed.
        cls.rebuild_chunks(document)

        cls._apply_importance(document)
        document.save()

        return document

    # ==========================================
    # 5. Text Chunking For RAG
    # ==========================================

    @classmethod
    def rebuild_chunks(cls, document):

        text = document.get_rag_text().strip()

        if not text:
            raise ValidationError(
                "Document has no content for RAG."
            )

        words = text.split()

        step = cls.CHUNK_SIZE - cls.CHUNK_OVERLAP

        chunks = []

        for start in range(0, len(words), step):

            chunk_words = words[
                start:start + cls.CHUNK_SIZE
            ]

            if not chunk_words:
                break

            chunks.append(
                KnowledgeChunk(
                    document=document,
                    chunk_index=len(chunks),
                    content=" ".join(chunk_words),
                    embedding=[],
                    is_embedded=False
                )
            )

            if start + cls.CHUNK_SIZE >= len(words):
                break

        # Delete old memory chunks only.
        document.chunks.all().delete()

        KnowledgeChunk.objects.bulk_create(chunks)

        return len(chunks)

    # ==========================================
    # 6. Importance Calculation
    # ==========================================

    @classmethod
    def _calculate_importance(cls, record):

        admin_score = (
            record.admin_importance * 10
        )

        access_score = min(
            record.access_count / 50,
            1
        ) * 35

        recency_score = 0

        if record.last_accessed_at:

            days = (
                timezone.now()
                - record.last_accessed_at
            ).total_seconds() / 86400

            recency_score = max(
                0,
                1 - days / 60
            ) * 15

        score = min(
            100,
            round(
                admin_score
                + access_score
                + recency_score
            )
        )

        if (
            record.is_protected
            or record.admin_importance >= 5
            or score >= 70
        ):
            level = cls.FREQUENT

        elif (
            record.admin_importance >= 3
            or score >= 35
        ):
            level = cls.NORMAL

        else:
            level = cls.LOW

        return score, level

    @classmethod
    def _apply_importance(cls, record):

        score, level = cls._calculate_importance(
            record
        )

        record.importance_score = score
        record.memory_level = level

        return record

    # ==========================================
    # 7. Record Product Access
    # ==========================================

    @classmethod
    def record_product_access(cls, memory_id):

        updated = ProductMemory.objects.filter(
            pk=memory_id
        ).update(
            access_count=F("access_count") + 1,
            last_accessed_at=timezone.now()
        )

        if not updated:
            raise ProductMemory.DoesNotExist

        memory = ProductMemory.objects.get(
            pk=memory_id
        )

        cls._apply_importance(memory)

        memory.save()

        return memory

    # ==========================================
    # 8. Record Knowledge Access
    # ==========================================

    @classmethod
    def record_knowledge_access(cls, chunk_id):

        now = timezone.now()

        with transaction.atomic():

            chunk = KnowledgeChunk.objects.get(
                pk=chunk_id
            )

            KnowledgeChunk.objects.filter(
                pk=chunk_id
            ).update(
                access_count=F("access_count") + 1,
                last_accessed_at=now
            )

            document = KnowledgeDocument.objects.get(
                pk=chunk.document_id
            )

            KnowledgeDocument.objects.filter(
                pk=document.pk
            ).update(
                access_count=F("access_count") + 1,
                last_accessed_at=now
            )

            document.refresh_from_db()

            cls._apply_importance(document)

            document.save()

        return chunk

    # ==========================================
    # 9. Requested Product Tracking
    # ==========================================

    @classmethod
    @transaction.atomic
    def record_requested_product(
        cls,
        requested_product_id,
        user=None,
        raw_query="",
        source="ai_chat"
    ):

        requested = (
            RequestedProduct.objects
            .select_for_update()
            .get(pk=requested_product_id)
        )

        now = timezone.now()

        ProductRequestEvent.objects.create(
            requested_product=requested,
            user=user,
            raw_query=raw_query,
            source=source
        )

        cutoff = now - timedelta(days=30)

        requested.total_requests += 1

        requested.requests_last_30_days = (
            requested.request_events.filter(
                created_at__gte=cutoff
            ).count()
        )

        requested.last_requested_at = now

        requested.save()

        return requested

    # ==========================================
    # 10. Cache Product Memory
    # ==========================================

    @classmethod
    def get_product_context(cls, product_id):

        memory = (
            ProductMemory.objects
            .select_related("product")
            .filter(
                product_id=product_id,
                product__status="published"
            )
            .first()
        )

        if memory is None:
            return None

        key = f"shop_memory:product:{product_id}"

        context = cache.get(key)

        if context is None:

            context = {
                "product_id": product_id,
                "summary": memory.summary,
                "searchable_text": memory.searchable_text,
                "keywords": memory.keywords,
                "attributes": memory.extracted_attributes,
            }

            if memory.memory_level == cls.FREQUENT:

                cache.set(
                    key,
                    context,
                    timeout=cls.CACHE_TIMEOUT
                )

        # Live commercial data is never read from cache.
        product = memory.product

        context["product"] = {
            "name": product.name,
            "price": str(product.current_price),
            "currency": product.currency_code,
            "stock": product.stock_quantity,
            "is_in_stock": product.is_in_stock,
        }

        cls.record_product_access(memory.pk)

        return context

    # ==========================================
    # 11. Cleanup Old Low-Importance Memory
    # ==========================================

    @classmethod
    def cleanup_low_memory(
        cls,
        inactive_days=None,
        dry_run=True
    ):

        if inactive_days is None:
            inactive_days = cls.INACTIVE_DAYS

        cutoff = (
            timezone.now()
            - timedelta(days=inactive_days)
        )

        product_memories = (
            ProductMemory.objects
            .filter(
                memory_level=cls.LOW,
                is_protected=False
            )
            .filter(
                Q(last_accessed_at__lt=cutoff)
                |
                Q(
                    last_accessed_at__isnull=True,
                    updated_at__lt=cutoff
                )
            )
        )

        knowledge_documents = (
            KnowledgeDocument.objects
            .filter(
                memory_level=cls.LOW,
                is_protected=False
            )
            .filter(
                Q(last_accessed_at__lt=cutoff)
                |
                Q(
                    last_accessed_at__isnull=True,
                    updated_at__lt=cutoff
                )
            )
        )

        requested_products = (
            RequestedProduct.objects
            .filter(
                demand_level=cls.LOW,
                is_protected=False,
                last_requested_at__lt=cutoff
            )
        )

        result = {
            "product_memories": product_memories.count(),
            "knowledge_documents": knowledge_documents.count(),
            "requested_products": requested_products.count(),
            "dry_run": dry_run,
        }

        if dry_run:
            return result

        product_ids = list(
            product_memories.values_list(
                "product_id",
                flat=True
            )
        )

        with transaction.atomic():

            product_memories.delete()

            # Deleting a document also deletes its chunks.
            knowledge_documents.delete()

            # Only requested-product memory is deleted.
            requested_products.delete()

        for product_id in product_ids:

            cache.delete(
                f"shop_memory:product:{product_id}"
            )

        return result
