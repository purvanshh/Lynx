import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from lynx.api.dependencies import get_orchestrator, get_store
from lynx.api.routes.health import router as health_router
from lynx.api.routes.participants import router as participants_router
from lynx.api.routes.sessions import router as sessions_router
from lynx.api.routes.ws import router as ws_router
from lynx.api.ws_manager import ws_manager
from lynx.config import get_settings
from lynx.models.session import ConfidenceHistoryEntry
from lynx.utils.logging import configure_logging
from lynx.utils.time import utc_now

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_heartbeat_loop())
    yield
    task.cancel()


async def _heartbeat_loop() -> None:
    while True:
        await asyncio.sleep(30)
        store = get_store()
        orchestrator = get_orchestrator()
        session_ids = store.get_all_session_ids()
        for session_id in session_ids:
            session = store.get(session_id)
            if session is None or not session.participants:
                continue
            output = orchestrator.evaluate(session)
            session.prior_probabilities = output.candidate_probabilities
            session.confidence_history.append(
                ConfidenceHistoryEntry(
                    timestamp=utc_now(),
                    probabilities=output.candidate_probabilities,
                )
            )
            store.update(session)
            await ws_manager.broadcast(
                session_id,
                {
                    "type": "heartbeat_update",
                    "session_id": session_id,
                    "data": {
                        "participant_id": output.top_candidate_id,
                        "candidate_probability": output.top_candidate_probability,
                        "confidence_tier": output.confidence_tier,
                        "is_candidate": output.confidence_tier in {"HIGH", "MEDIUM"},
                        "candidate_probabilities": output.candidate_probabilities,
                        "evidence": {
                            pid: [item.model_dump(mode="json") for item in items]
                            for pid, items in output.evidence.items()
                        },
                        "arbitrator_explanation": output.arbitrator_explanation,
                        "updated_at": output.updated_at.isoformat(),
                    },
                },
            )


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled API exception", request_id=request_id, path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(participants_router)
app.include_router(ws_router)
