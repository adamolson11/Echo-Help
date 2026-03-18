from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_ask_echo_logs_list_and_detail_smoke():
  # Trigger at least one ask-echo call so a log entry exists
  r = client.post("/api/ask-echo", json={"q": "test ask echo logs", "limit": 3})
  assert r.status_code == 200

  # List logs
  r = client.get("/api/ask-echo/logs?limit=5")
  assert r.status_code == 200
  data = r.json()
  assert isinstance(data, list)
  assert len(data) >= 1
  log_id = data[0]["id"]

  # Fetch detail for first log
  r2 = client.get(f"/api/ask-echo/logs/{log_id}")
  assert r2.status_code == 200
  detail = r2.json()
  assert detail["id"] == log_id
  assert isinstance(detail["answer_text"], str)
  assert "reasoning" in detail
  assert "candidate_snippets" in detail["reasoning"]
  assert "chosen_snippet_ids" in detail["reasoning"]
  assert "reasoning_notes" in detail
