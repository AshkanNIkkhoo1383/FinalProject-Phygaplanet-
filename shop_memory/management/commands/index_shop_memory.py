
from django.core.management.base import (
    BaseCommand
)

from shop_memory.rag.indexer import MemoryIndexer


class Command(BaseCommand):

    help = "Generate pending Shop Memory embeddings."

    def add_arguments(self, parser):

        parser.add_argument(
            "--batch-size",
            type=int,
            default=16
        )

    def handle(self, *args, **options):

        batch_size = options["batch_size"]

        total_products = 0
        total_chunks = 0

        while True:

            result = MemoryIndexer.index_pending(
                batch_size=batch_size
            )

            products = result["products"]
            chunks = result["chunks"]

            total_products += products
            total_chunks += chunks

            if products == 0 and chunks == 0:
                break

            self.stdout.write(
                f"Indexed products: {products}, "
                f"chunks: {chunks}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Indexing completed. "
                f"Products: {total_products}, "
                f"Chunks: {total_chunks}"
            )
        )
