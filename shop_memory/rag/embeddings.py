
import numpy as np

from django.conf import settings


class EmbeddingService:

    _model = None

    @classmethod
    def model_name(cls):

        return getattr(
            settings,
            "SHOP_MEMORY_EMBEDDING_MODEL",
            "intfloat/multilingual-e5-small"
        )

    @classmethod
    def get_model(cls):

        if cls._model is None:

            try:
                from sentence_transformers import (
                    SentenceTransformer
                )

                # CPU only: no GPU required.
                cls._model = SentenceTransformer(
                    cls.model_name(),
                    device="cpu"
                )

            except Exception as exc:

                raise RuntimeError(
                    "Could not load the embedding model."
                ) from exc

        return cls._model

    @classmethod
    def encode_query(cls, text):

        model = cls.get_model()

        vector = model.encode(
            ["query: " + text],
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        )[0]

        return np.asarray(
            vector,
            dtype=np.float32
        )

    @classmethod
    def encode_passages(cls, texts):

        if not texts:
            return []

        model = cls.get_model()

        prepared_texts = [
            "passage: " + text
            for text in texts
        ]

        vectors = model.encode(
            prepared_texts,
            batch_size=8,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        return np.asarray(
            vectors,
            dtype=np.float32
        )
