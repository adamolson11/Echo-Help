import re
import string

STOPWORDS = {"the", "a", "an", "to", "and", "user"}


def normalize_phrase(text: str) -> str:
    """
    Normalize free-text fix phrases for grouping and embeddings.

    Rules:
    - lowercase
    - strip leading/trailing whitespace
    - remove punctuation
    - collapse repeated spaces
    - remove trivial stopwords
    - if everything stripped, fall back to cleaned original
    """
    if text is None:
        return ""

    t = text.lower().strip()

    # remove punctuation
    t = t.translate(str.maketrans("", "", string.punctuation))

    # collapse whitespace
    t = re.sub(r"\s+", " ", t)

    # remove stopwords
    tokens = [tok for tok in t.split() if tok not in STOPWORDS]

    if not tokens:
        return t

    return " ".join(tokens)
