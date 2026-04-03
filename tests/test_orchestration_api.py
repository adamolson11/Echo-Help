from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def _payload() -> dict[str, object]:
    return {
        "command": "Reset stuck sync queue",
        "archive_seed": ["Investigate stale archive", "Investigate stale archive"],
        "agents": [
            {
                "name": "triage",
                "role": "triage",
                "focus": ["Reset stuck sync queue", "Clear duplicate notifications"],
            },
            {
                "name": "ops",
                "role": "execution",
                "focus": ["Clear duplicate notifications", "Investigate stale archive"],
            },
        ],
    }


def test_orchestration_cycle_contract_and_persistence() -> None:
    resp = client.post("/api/orchestration/cycles", json=_payload())
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["meta"] == {"kind": "orchestration_cycle", "version": "v1"}
    assert data["status"] == "completed"
    assert data["current_stage"] == "next_cycle_prepared"
    assert len(data["agent_passes"]) == 2
    assert all(agent_pass["pass_index"] == 1 for agent_pass in data["agent_passes"])
    assert all(agent_pass["format_version"] == "v1" for agent_pass in data["agent_passes"])
    assert [item["stage"] for item in data["stage_history"]] == [
        "command_received",
        "agent_passes_completed",
        "outputs_cleaned",
        "workflow_generated",
        "work_executed",
        "outcomes_archived",
        "next_cycle_prepared",
    ]
    assert data["cleaned_output"]["actions"] == [
        "Reset stuck sync queue",
        "Clear duplicate notifications",
        "Investigate stale archive",
    ]
    assert [item["title"] for item in data["daily_workflow"]["items"]] == data["cleaned_output"]["actions"]
    assert data["next_cycle_seed"] == data["archive"]["next_cycle_seed"]

    detail = client.get(f"/api/orchestration/cycles/{data['cycle_id']}")
    assert detail.status_code == 200, detail.text
    detail_data = detail.json()
    assert detail_data["cycle_id"] == data["cycle_id"]
    assert detail_data["cleaned_output"] == data["cleaned_output"]
    assert detail_data["daily_workflow"] == data["daily_workflow"]


def test_orchestration_cycle_archive_replay_uses_cleaned_seed() -> None:
    first = client.post("/api/orchestration/cycles", json=_payload())
    assert first.status_code == 200, first.text
    first_id = first.json()["cycle_id"]

    second = client.post(
        "/api/orchestration/cycles",
        json={
            "command": "Investigate stale archive",
            "seed_cycle_id": first_id,
            "agents": [
                {"name": "audit", "role": "audit", "focus": ["Investigate stale archive"]},
            ],
        },
    )
    assert second.status_code == 200, second.text
    data = second.json()

    assert data["seeded_from_cycle_id"] == first_id
    assert data["cleaned_output"]["archive_seed"] == [
        "Reset stuck sync queue",
        "Clear duplicate notifications",
        "Investigate stale archive",
    ]
    assert data["cleaned_output"]["actions"] == [
        "Investigate stale archive",
        "Reset stuck sync queue",
        "Clear duplicate notifications",
    ]


def test_orchestration_cycle_generation_is_idempotent() -> None:
    first = client.post("/api/orchestration/cycles", json=_payload())
    second = client.post("/api/orchestration/cycles", json=_payload())
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    first_data = first.json()
    second_data = second.json()
    assert first_data["daily_workflow"] == second_data["daily_workflow"]
    assert first_data["next_cycle_seed"] == second_data["next_cycle_seed"]


def test_orchestration_cycle_requires_strict_input() -> None:
    resp = client.post(
        "/api/orchestration/cycles",
        json={"command": "   ", "agents": [{"name": "triage", "role": "triage"}]},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "command is required"
