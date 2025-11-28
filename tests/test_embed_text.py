from backend.app.services.embeddings import embed_text


def test_embed_text_single():
    vec = embed_text("test sentence")
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert all(isinstance(x, float) for x in vec[:5])


def test_embed_text_batch():
    vecs = embed_text(["one", "two"])
    assert isinstance(vecs, list)
    assert len(vecs) == 2
    assert all(isinstance(x, list) for x in vecs)
