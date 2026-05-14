"""
backend/app/main.py  — UPDATED VERSION
Only the auth lines are new. Everything else is unchanged from your original.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    extract, apply, ingest, profile,
    feedback, rules, validate, health,
    actions, mapping, rule_validation,
    auth,                                  # ← NEW
)
from .db import base


def create_app() -> FastAPI:
    app = FastAPI(title="CleanPilot", description="Intelligent Data Cleaning Assistant")

    # Create all tables (including new users table)
    try:
        base.Base.metadata.create_all(bind=base.engine, checkfirst=True)
    except Exception as e:
        print(f"Warning: Database initialization issue: {e}")

    @app.get("/")
    def root():
        return {"message": "CleanPilot API", "version": "2.0.0", "docs": "/docs"}

    # ── Existing routers (unchanged) ──────────────────────────────────────────
    app.include_router(health.router,           prefix="/health",          tags=["health"])
    app.include_router(ingest.router,           prefix="/ingest",          tags=["ingest"])
    app.include_router(profile.router,          prefix="/profile",         tags=["profile"])
    app.include_router(extract.router,          prefix="/extract",         tags=["rule-extraction"])
    app.include_router(rules.router,            prefix="/rules",           tags=["rules"])
    app.include_router(apply.router,            prefix="/apply",           tags=["apply"])
    app.include_router(validate.router,         prefix="/validate",        tags=["validate"])
    app.include_router(feedback.router,         prefix="/feedback",        tags=["feedback"])
    app.include_router(actions.router,          prefix="/actions",         tags=["actions"])
    app.include_router(mapping.router,          prefix="/mapping",         tags=["mapping"])
    app.include_router(rule_validation.router,  prefix="/rule-validation", tags=["rule-validation"])

    from .api import runs as runs_api
    app.include_router(runs_api.router, prefix="/runs", tags=["runs"])

    # ── NEW: Auth router ──────────────────────────────────────────────────────
    app.include_router(auth.router, prefix="/auth", tags=["auth"])

    # ── CORS (updated to allow longer token headers) ──────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = create_app()
