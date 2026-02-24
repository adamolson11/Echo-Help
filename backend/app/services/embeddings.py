from collections.abc import Sequence
import os

DISABLE_EMBEDDINGS = os.getenv("DISABLE_EMBEDDINGS", "").lower() in ("1", "true", "yes")

# Name of the embedding model we use everywhere
MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def _raise_disabled() -> None:
    raise RuntimeError("Embeddings disabled (DISABLE_EMBEDDINGS=1)")


if not DISABLE_EMBEDDINGS:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    def _get_model():
        global _model
        if _model is None:
            _model = SentenceTransformer(MODEL_NAME)
        return _model

    def cosine_similarity(a, b):
        """
        Compute cosine similarity between two vectors (lists or numpy arrays).
        """
        va = np.array(a)
        vb = np.array(b)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)

    def embed_text(text: str | Sequence[str]):
        """
        Return embeddings as Python lists.
        If a single string is passed, return a single vector.
        If a list of strings is passed, return a list of vectors.
        """
        if isinstance(text, str):
            texts = [text]
            single = True
        else:
            texts = text
            single = False

        model = _get_model()
        # The SentenceTransformer encode API may return numpy arrays or tensors
        # depending on environment; coerce to numpy array and then tolist for a
        # predictable Python list return type. Narrow-ignore where external stubs
        # are incomplete.
        embeddings_np = model.encode(texts, convert_to_numpy=True)  # type: ignore[reportUnknownMemberType]
        arr = np.asarray(embeddings_np)
        lists = arr.tolist()
        return lists[0] if single else lists
else:
    def cosine_similarity(a, b):
        _raise_disabled()

    def embed_text(text: str | Sequence[str]):
        _raise_disabled()
