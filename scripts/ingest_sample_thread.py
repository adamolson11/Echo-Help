import json
from sqlmodel import Session

from backend.app.db import engine, init_db
from backend.app.schemas.ingest import IngestThread
from backend.app.services.ingest import ingest_thread


def main() -> None:
    init_db()
    with open("sample_data/sample_thread_slack.json") as f:
        data = json.load(f)

    thread = IngestThread(**data)

    with Session(engine) as session:
        ticket = ingest_thread(thread, session)
        print("Created ticket:", ticket.id, ticket.summary)


if __name__ == "__main__":
    main()
