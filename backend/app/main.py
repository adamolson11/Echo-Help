from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import init_db
from .api import health, tickets, search, intake, feedback
from .api.routes import ticket_feedback
from .api.routes import insights

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
    app.include_router(intake.router, prefix="/api")
    app.include_router(feedback.router, prefix="/api")


    app.include_router(ticket_feedback.router)
    app.include_router(insights.router)
    return app

app = create_app()
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "EchoHelp backend",
        "message": "Backend running. See /docs for API docs."
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}