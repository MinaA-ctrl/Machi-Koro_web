"""FastAPI app for the new Stage-2 backend (S2.3 — REST surface).

PARALLEL BUILD — not serving live. The live MVP still runs `websocket-server/main.py`
on MySQL; at the S2.6/S2.7 cutover the entrypoint switches to this `app`. Imports
the headless engine (`machi_koro_engine`) and the Postgres repository
(`persistence`); auth is the S2.3 guest-identity stand-in (JWT lands in S2.4).
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import ws
from app.config import require_secrets
from app.reaper import reaper_loop
from app.routers import auth, tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    require_secrets()  # in prod, refuse to boot on missing/insecure secrets (S2.6a)
    reaper = asyncio.create_task(reaper_loop())  # background table-lifecycle cleanup
    try:
        yield
    finally:
        reaper.cancel()


app = FastAPI(title="Machi Koro Backend (Stage 2)", version="2.6.0", lifespan=lifespan)
app.include_router(auth.router)    # JWT auth: register/login/guest/refresh/me (S2.4)
app.include_router(tables.router)
app.include_router(ws.router)  # game + lobby WebSockets (S2.3b)


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok"}
