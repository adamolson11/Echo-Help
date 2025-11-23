from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db
from .api import health, tickets, search

def create_app():
    app = FastAPI(title="EchoHelp API", version="0.1.0")

    # Allow CORS for local frontend dev (adjust origins as needed)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For dev only; restrict in prod
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()

    app.include_router(health.router, prefix="/api")
    app.include_router(tickets.router, prefix="/api")
    app.include_router(search.router, prefix="/api")

    return app

app = create_app()