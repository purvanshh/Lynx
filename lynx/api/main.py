import asyncio
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from lynx.api.anomaly import check_anomalies
from lynx.api.dependencies import get_orchestrator, get_store
from lynx.api.metrics import (
    active_sessions,
    anomaly_counter,
    confidence_tier_gauge,
    http_request_duration,
    top_probability_gauge,
)
from lynx.api.routes.analytics import router as analytics_router
from lynx.api.routes.health import router as health_router
from lynx.api.routes.participants import router as participants_router
from lynx.api.routes.sessions import router as sessions_router
from lynx.api.routes.ws import router as ws_router
from lynx.api.ws_manager import ws_manager
from lynx.config import get_settings
from lynx.models.evidence import ArbitratorOutput
from lynx.models.session import ConfidenceHistoryEntry
from lynx.utils.logging import configure_logging
from lynx.utils.time import utc_now

settings = get_settings()
configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)

_prev_outputs: dict[str, ArbitratorOutput] = {}

_TIER_MAP = {"HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNCERTAIN": 4}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_heartbeat_loop())
    yield
    task.cancel()


async def _heartbeat_loop() -> None:
    while True:
        await asyncio.sleep(30)
        store = get_store()
        orchestrator = get_orchestrator()
        session_ids = store.get_all_session_ids()
        active_sessions.set(len(session_ids))
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

            tier_val = _TIER_MAP.get(output.confidence_tier, 4)
            confidence_tier_gauge.labels(session_id=session_id).set(tier_val)
            top_probability_gauge.labels(session_id=session_id).set(
                output.top_candidate_probability
            )

            prev = _prev_outputs.get(session_id)
            anomalies = check_anomalies(session, output, prev)
            _prev_outputs[session_id] = output

            for alert in anomalies:
                anomaly_counter.labels(rule=alert.rule).inc()
                logger.info("anomaly_detected", rule=alert.rule, session_id=session_id, message=alert.message)

            heartbeat_data = {
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
            }
            msg: dict[str, object] = {
                "type": "heartbeat_update",
                "session_id": session_id,
                "data": heartbeat_data,
            }
            if anomalies:
                msg["anomalies"] = [
                    {"rule": a.rule, "severity": a.severity, "message": a.message, "details": a.details}
                    for a in anomalies
                ]
            await ws_manager.broadcast(session_id, msg)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    path = request.url.path
    if not path.startswith("/metrics"):
        http_request_duration.labels(method=request.method, path=path).observe(elapsed)
    return response


@app.middleware("http")
async def add_request_context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
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


@app.get("/metrics", include_in_schema=False)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(analytics_router)
app.include_router(health_router)
app.include_router(sessions_router)
app.include_router(participants_router)
app.include_router(ws_router)
