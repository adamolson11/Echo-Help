from pathlib import Path
import os

from sqlmodel import Session, SQLModel, create_engine

# Allow configuring the DB path via env var to support Docker volumes.
# Default to repo-root `echohelp.db` for local dev.
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = os.getenv("ECHOHELP_DB_PATH", str(BASE_DIR / "echohelp.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
