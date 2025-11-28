from fastapi.testclient import TestClient

from backend.app.db import get_session, init_db
from backend.app.main import app
from backend.app.models.embedding import Embedding
from backend.app.models.ticket import Ticket

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
