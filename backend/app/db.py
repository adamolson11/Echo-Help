def get_session():
	from sqlmodel import Session
	with Session(engine) as session:
		yield session
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "sqlite:///./echohelp.db"

engine = create_engine(
	DATABASE_URL,
	echo=False,
	connect_args={"check_same_thread": False}
)

def init_db():
	from . import models
	SQLModel.metadata.create_all(engine)

def get_session():
	with Session(engine) as session:
		yield session
