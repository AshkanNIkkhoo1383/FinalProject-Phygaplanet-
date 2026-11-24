
from django.utils import timezone

from shop_memory.models import (
    ProductMemory,
    KnowledgeChunk,
)

from .embeddings import EmbeddingService


class MemoryIndexer:

    @classmethod
    def index_pending(cls, batch_size=16):

        result = {
            "products": 0,
            "chunks": 0,
        }

        # ======================================
        # 1. Product Memory
        # ======================================

        product_memories = list(
            ProductMemory.objects.filter(
                index_status="pending"
            )[:batch_size]
        )

        product_texts = [
            memory.searchable_text
            for memory in product_memories
        ]

        if product_texts:

            vectors = EmbeddingService.encode_passages(
                product_texts
            )

            for memory, vector in zip(
                product_memories,
                vectors
            ):

                memory.embedding = vector.tolist()

                memory.embedding_model = (
                    EmbeddingService.model_name()
                )

                memory.index_status = "ready"

                memory.indexed_at = timezone.now()

                memory.save(
                    update_fields=[
                        "embedding",
                        "embedding_model",
                        "index_status",
                        "indexed_at",
                        "updated_at",
                    ]
                )

                result["products"] += 1

        # ======================================
        # 2. Knowledge Chunks
        # ======================================

        chunks = list(
            KnowledgeChunk.objects.filter(
                is_embedded=False,
                document__status="published"
            ).select_related(
                "document"
            )[:batch_size]
        )

        chunk_texts = [
            chunk.content
            for chunk in chunks
        ]

        if chunk_texts:

            vectors = EmbeddingService.encode_passages(
                chunk_texts
            )

            for chunk, vector in zip(
                chunks,
                vectors
            ):

                chunk.embedding = vector.tolist()

                chunk.embedding_model = (
                    EmbeddingService.model_name()
                )

                chunk.is_embedded = True

                chunk.save(
                    update_fields=[
                        "embedding",
                        "embedding_model",
                        "is_embedded",
                    ]
                )

                result["chunks"] += 1

        return result
