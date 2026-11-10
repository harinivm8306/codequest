"""SchemeSathi API. Live docs at /docs."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal, init_db
from app.routers import chat, documents, eligibility, profiles
from app.services import bhashini, rules
from app.services.doc_doctor import _tesseract_langs
from app.services.housekeeping import cleanup

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("schemesathi")


async def _housekeeping_loop():
    while True:
        try:
            log.info("cleanup: %s", cleanup())
        except Exception as exc:  # never crash the app over housekeeping
            log.warning("cleanup failed: %s", exc)
        await asyncio.sleep(3600)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    rules.load_schemes()
    if settings.hash_salt == "dev-only-salt-change-me":
        log.warning("HASH_SALT is the development default. Set a long random HASH_SALT before deploying.")
    task = asyncio.create_task(_housekeeping_loop())
    yield
    task.cancel()


app = FastAPI(
    title="SchemeSathi API",
    version="1.0.0",
    lifespan=lifespan,
    description="Voice-first welfare scheme eligibility. The rules engine, not the language model, decides eligibility.",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "error", "message": str(exc.detail)}
    return JSONResponse({"error": detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    msg = f"{'.'.join(str(x) for x in first.get('loc', []))}: {first.get('msg', 'invalid request')}"
    return JSONResponse({"error": {"code": "validation_error", "message": msg}}, status_code=422)


@app.get("/api/v1/health")
def health():
    db = "ok"
    try:
        with SessionLocal() as s:
            s.execute(text("select 1"))
    except Exception:
        db = "down"
    return {
        "status": "ok",
        "db": db,
        "bhashini": bhashini.status(),
        "llm": "claude" if settings.llm_enabled else "keywords",
        "ocr_languages": _tesseract_langs(),
        "schemes": len(rules.load_schemes()),
        "rules_version": rules.rules_version(),
    }


for r in (profiles.router, chat.router, eligibility.router, documents.router):
    app.include_router(r, prefix="/api/v1")

# Optional: serve the exported frontend from the same service (one free-tier deploy).
dist = Path(settings.frontend_dist)
if dist.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = (dist / path).resolve()
        if dist.resolve() in target.parents or target == dist.resolve():
            if target.is_file():
                return FileResponse(target)
            if (target / "index.html").is_file():
                return FileResponse(target / "index.html")
            if target.with_suffix(".html").is_file():
                return FileResponse(target.with_suffix(".html"))
        return FileResponse(dist / "index.html")
