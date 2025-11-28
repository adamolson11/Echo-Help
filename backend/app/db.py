from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

# Use a repo-root absolute path so the same database file is used
# regardless of the current working directory when starting the server.
BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_URL = f"sqlite:///{BASE_DIR / 'echohelp.db'}"

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
