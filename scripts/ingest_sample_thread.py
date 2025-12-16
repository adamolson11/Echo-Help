import json
from sqlmodel import Session

import backend.app.db as db
from backend.app.schemas.ingest import IngestThread
from backend.app.services.ingest import ingest_thread


def main() -> None:
    db.init_db()
    if db.engine is None:
        raise SystemExit("Database engine is not initialized")
    with open("sample_data/sample_thread_slack.json") as f:
        data = json.load(f)

    thread = IngestThread(**data)

    with Session(db.engine) as session:
        ticket = ingest_thread(thread, session)
        print("Created ticket:", ticket.id, ticket.summary)


if __name__ == "__main__":
    main()
