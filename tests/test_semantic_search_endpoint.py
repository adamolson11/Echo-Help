from fastapi.testclient import TestClient

from backend.app.db import get_session, init_db
from backend.app.main import app
from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket
from backend.app.services.embeddings import embed_text

client = TestClient(app)


def seed_ticket_with_embedding():
    # ensure tables
    init_db()
    with next(get_session()) as session:
        # create a ticket
        t = Ticket(
            external_key="T-1",
            source="test",
            project_key="IT",
            summary="VPN not connecting",
            description="User cannot connect to VPN",
            status="open",
            priority="medium",
        )
        session.add(t)
        session.commit()
        session.refresh(t)

        # simple embedding vector (small dimension) to test pipeline
        emb = Embedding(ticket_id=t.id, text=t.summary, vector=[0.1, 0.2, 0.3])
        session.add(emb)
        session.commit()
        session.refresh(emb)
        return t


def test_semantic_search_smoke():
    seed_ticket_with_embedding()
    resp = client.post("/api/semantic-search", json={"q": "vpn connection issue", "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # result items should have at least ticket_id and score
    if data:
        item = data[0]
        assert "ticket_id" in item
        assert "score" in item


def test_semantic_search_limit_and_filters():
    # ensure tables
    init_db()
    # get a real embedding vector for the query so dimensionality matches
    qvec = embed_text("password reset")

    with next(get_session()) as session:
        # create several tickets with varying status/priorities
        t1 = Ticket(
            external_key="T-2",
            source="test",
            project_key="IT",
            summary="Password reset fails",
            description="User cannot reset password",
            status="open",
            priority="high",
        )
        t2 = Ticket(
            external_key="T-3",
            source="test",
            project_key="IT",
            summary="Password email not received",
            description="User does not get reset email",
            status="closed",
            priority="low",
        )
        t3 = Ticket(
            external_key="T-4",
            source="test",
            project_key="IT",
            summary="Reset token expired",
            description="Token expired immediately",
            status="open",
            priority="medium",
        )

        session.add_all([t1, t2, t3])
        session.commit()
        session.refresh(t1)
        session.refresh(t2)
        session.refresh(t3)

        # attach embeddings using the same query vector so they are comparable
        e1 = Embedding(ticket_id=t1.id, text=t1.summary, vector=qvec)
        e2 = Embedding(ticket_id=t2.id, text=t2.summary, vector=qvec)
        e3 = Embedding(ticket_id=t3.id, text=t3.summary, vector=qvec)
        session.add_all([e1, e2, e3])
        session.commit()

    # Test limit respected
    resp = client.post("/api/semantic-search", json={"q": "password reset", "limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 2

    # Test filters: status=open should only return open tickets
    resp2 = client.post("/api/semantic-search", json={"q": "password reset", "limit": 10, "status": "open"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert isinstance(data2, list)
    # every returned item should correspond to an open ticket
    for item in data2:
        # fetch ticket to check status
        with next(get_session()) as session:
            t = session.get(Ticket, item.get("ticket_id"))
            assert t is not None
            assert t.status and "open" in t.status.lower()
