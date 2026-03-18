import hashlib
import logging
import math
import os
from collections.abc import Sequence

_LOGGER = logging.getLogger(__name__)
_LOGGED_DISABLED = False


def _is_disabled_by_env() -> bool:
    value = os.getenv("ECHO_EMBEDDINGS", "").strip().lower()
    return value in {"0", "off", "false", "no", "disabled"}


MODEL_NAME = "all-MiniLM-L6-v2"
_model = None
_DISABLED_REASON: str | None = None

if _is_disabled_by_env():
    _DISABLED_REASON = "ECHO_EMBEDDINGS=off"
else:
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        if exc.name == "sentence_transformers":
            _DISABLED_REASON = "sentence_transformers not installed"
        else:
            _DISABLED_REASON = f"missing dependency: {exc.name}"


def embeddings_enabled() -> bool:
    return _DISABLED_REASON is None


def _log_disabled_once() -> None:
    global _LOGGED_DISABLED
    if _LOGGED_DISABLED:
        return
    _LOGGED_DISABLED = True
    reason = _DISABLED_REASON or "unknown reason"
    _LOGGER.warning("Embeddings disabled: %s", reason)


def log_embeddings_disabled_once() -> None:
    _log_disabled_once()


def _fallback_vector(text: str, dim: int = 8) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8", "ignore")).digest()
    return [b / 255.0 for b in digest[:dim]]


if embeddings_enabled():

    def _get_model():
        global _DISABLED_REASON, _model
        if _model is None:
            try:
                _model = SentenceTransformer(MODEL_NAME)
            except Exception as exc:
                _DISABLED_REASON = f"model load failed: {type(exc).__name__}"
                _log_disabled_once()
                return None
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

    def embed_text(text: str | Sequence[str]):  # pyright: ignore[reportRedeclaration]
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
        if model is None:
            if single:
                return _fallback_vector(texts[0])
            return [_fallback_vector(item) for item in texts]
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
        _log_disabled_once()
        if not a or not b:
            return 0.0
        length = min(len(a), len(b))
        if length == 0:
            return 0.0
        dot = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for i in range(length):
            va = float(a[i])
            vb = float(b[i])
            dot += va * vb
            norm_a += va * va
            norm_b += vb * vb
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def embed_text(text: str | Sequence[str]):
        _log_disabled_once()
        if isinstance(text, str):
            return _fallback_vector(text)
        return [_fallback_vector(item) for item in text]
