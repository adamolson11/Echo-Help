import numpy as np

def cosine_similarity(a, b):
    """
    Compute cosine similarity between two vectors (lists or numpy arrays).
    """
    va = np.array(a)
    vb = np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)

from sentence_transformers import SentenceTransformer

# Name of the embedding model we use everywhere
MODEL_NAME = "all-MiniLM-L6-v2"

_model = SentenceTransformer(MODEL_NAME)

def embed_text(text: str):
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

    embeddings = _model.encode(texts, convert_to_numpy=True).tolist()
    return embeddings[0] if single else embeddings
