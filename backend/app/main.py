import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# ...existing imports...
from . import db
from .api import (
    feedback,
    feedback_suggestions,
    health,
    intake,
    search,
    semantic_clusters,
    semantic_search,
    tickets,
)
from .api.routes import (
    ask_echo,
    ingest,
    insights,
    machine,
    orchestration,
    patterns,
    snippets,
    ticket_feedback,
)

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB schema exists at application startup. This is important
    # for TestClient-based tests which import `app` and start the ASGI
    # app lifecycle; calling `init_db()` here makes table creation
    # deterministic regardless of test import order.
    db.init_db()

    # Seed demo data on first run so the product is ready to explore out of
    # the box (QA, demos, local dev). Both helpers are idempotent — they check
    # for existing rows before inserting, so re-runs are safe.
    try:
        from .db_init import seed_tickets

        seed_tickets()
    except Exception as exc:
        _log.warning("seed_tickets() skipped: %s", exc)

    try:
        from scripts.seed_demo_org import seed_demo_org  # type: ignore

        seed_demo_org()
    except Exception as exc:
        _log.warning("seed_demo_org() skipped: %s", exc)

    yield


app = FastAPI(lifespan=lifespan)


## DEV: Previously had an Eat401Middleware here that intercepted 401s
## and converted them to 200 for /api/search. Commenting it out for
## the simpler dev flow requested (no auth middleware interference).
# class Eat401Middleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         response = await call_next(request)
#         # Debug print so we can see what's going on
#         if response.status_code == 401:
#             print("EAT401 MIDDLEWARE: intercepted 401 for path:", request.url.path)
#         # For /api/search, turn any 401 into a 200 with empty ticket list
#         if response.status_code == 401 and request.url.path.startswith("/api/search"):
#             return Response(
#                 content="[]",
#                 media_type="application/json",
#                 status_code=200,
#             )
#         return response

# app.add_middleware(Eat401Middleware)

# ✅ DEV CORS: allow everything
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow any origin
    allow_credentials=False,  # MUST be False when allow_origins=["*"]
    allow_methods=["*"],  # allow all HTTP verbs
    allow_headers=["*"],  # allow all headers
)

# Note: `init_db()` will be invoked at application startup via
# the `startup` event handler below. This ensures tests can set
# `ECHOHELP_DB_PATH` before the app lifecycle triggers schema
# creation and avoids creating the DB at import time.

# ⬅️ include your routers AFTER the middleware is added
app.include_router(health.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
# Restore real search router
app.include_router(search.router, prefix="/api")
app.include_router(intake.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(ticket_feedback.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(ask_echo.router, prefix="/api")
app.include_router(snippets.router, prefix="/api")
app.include_router(machine.router, prefix="/api")
app.include_router(orchestration.router, prefix="/api")
app.include_router(feedback_suggestions.router, prefix="/api")
app.include_router(semantic_search.router, prefix="/api")
app.include_router(semantic_clusters.router, prefix="/api")
app.include_router(patterns.router, prefix="/api", tags=["patterns"])


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "EchoHelp backend",
        "message": "Backend running. See /docs for API docs.",
    }


@app.get("/health")
async def health_check():
    # Basic DB connectivity check
    db_ok = False
    try:
        db.ensure_engine()
        if db.engine is None:
            raise RuntimeError("DB engine not initialized")
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "ok",
        "service": "echohelp-backend",
        "version": os.getenv("ECHOHELP_VERSION", "0.1.0"),
        "db_ok": db_ok,
    }


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
