from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException

from lynx.api.dependencies import get_orchestrator, get_store
from lynx.api.schemas import CreateSessionRequest, EventRequest, FeedbackRequest
from lynx.api.ws_manager import ws_manager
from lynx.arbitrator.weights import adapt_weights_from_feedback
from lynx.models.evidence import ArbitratorOutput
from lynx.models.participant import Participant, WebcamFrame
from lynx.models.session import ConfidenceHistoryEntry, SessionEventEntry, SessionState
from lynx.models.transcript import TranscriptUtterance
from lynx.orchestrator import AgentOrchestrator
from lynx.store.memory_store import InMemorySessionStore
from lynx.utils.time import utc_now

router = APIRouter(prefix="/sessions", tags=["sessions"])

logger = structlog.get_logger(__name__)


def _find_participant(session: SessionState, participant_id: str) -> Participant:
    participant = next(
        (participant for participant in session.participants if participant.participant_id == participant_id),
        None,
    )
    if participant is None:
        raise HTTPException(status_code=404, detail=f"Participant '{participant_id}' not found")
    return participant


@router.post("")
def create_session(
    request: CreateSessionRequest,
    store: InMemorySessionStore = Depends(get_store),
) -> dict[str, str]:
    timestamp = utc_now()
    session = SessionState(
        session_id=str(uuid4()),
        candidate_name=request.candidate_name,
        candidate_email=request.candidate_email,
        interviewer_names=request.interviewer_names,
        scheduled_start_time=request.scheduled_start_time,
        calendar_invite_text=request.calendar_invite_text,
        created_at=timestamp,
        current_time=timestamp,
    )
    store.create(session)
    return {"session_id": session.session_id, "status": "created"}


@router.get("/{session_id}")
def get_session(
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
) -> SessionState:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/events")
async def inject_event(
    session_id: str,
    event: EventRequest,
    store: InMemorySessionStore = Depends(get_store),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, str]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if event.type == "participant_join":
        if not event.participant_id or not event.display_name:
            raise HTTPException(status_code=400, detail="participant_join requires participant_id and display_name")
        participant = next(
            (item for item in session.participants if item.participant_id == event.participant_id),
            None,
        )
        if participant is None:
            session.participants.append(
                Participant(
                    participant_id=event.participant_id,
                    display_name=event.display_name,
                    join_timestamp=event.timestamp,
                    webcam_on=event.webcam_on or False,
                )
            )
            display_name = event.display_name
        else:
            participant.display_name = event.display_name
            participant.join_timestamp = event.timestamp
            if event.webcam_on is not None:
                participant.webcam_on = event.webcam_on
            display_name = participant.display_name
        details = f"webcam_on={event.webcam_on}" if event.webcam_on is not None else None
    elif event.type == "participant_leave":
        if not event.participant_id:
            raise HTTPException(status_code=400, detail="participant_leave requires participant_id")
        participant = _find_participant(session, event.participant_id)
        participant.leave_timestamp = event.timestamp
        display_name = participant.display_name
        details = None
    elif event.type == "name_change":
        if not event.participant_id or not event.new_name:
            raise HTTPException(status_code=400, detail="name_change requires participant_id and new_name")
        participant = _find_participant(session, event.participant_id)
        participant.display_name = event.new_name
        display_name = participant.display_name
        details = f"renamed to {event.new_name}"
    elif event.type == "transcript":
        if not event.participant_id or event.utterance is None:
            raise HTTPException(status_code=400, detail="transcript requires participant_id and utterance")
        session.transcript.append(
            TranscriptUtterance(
                speaker_id=event.participant_id,
                utterance=event.utterance,
                timestamp=event.timestamp,
                duration_seconds=event.duration_seconds,
            )
        )
        participant = _find_participant(session, event.participant_id)
        participant.speaking_duration_total += event.duration_seconds or 0.0
        display_name = participant.display_name
        details = event.utterance
    elif event.type == "speaking_activity":
        if not event.participant_id:
            raise HTTPException(status_code=400, detail="speaking_activity requires participant_id")
        participant = _find_participant(session, event.participant_id)
        participant.speaking_activity.extend(event.activity)
        participant.speaking_duration_total += float(sum(1 for active in event.activity if active))
        display_name = participant.display_name
        details = f"{sum(1 for active in event.activity if active)} active seconds"
    elif event.type == "webcam_frame":
        if not event.participant_id:
            raise HTTPException(status_code=400, detail="webcam_frame requires participant_id")
        participant = _find_participant(session, event.participant_id)
        participant.webcam_frames.append(
            WebcamFrame(
                captured_at=event.timestamp,
                face_count=event.face_count,
                image_path=event.image_path,
            )
        )
        if event.webcam_on is not None:
            participant.webcam_on = event.webcam_on
        display_name = participant.display_name
        details = f"face_count={event.face_count}" if event.face_count is not None else "frame sampled"
    elif event.type == "screen_share":
        if not event.participant_id:
            raise HTTPException(status_code=400, detail="screen_share requires participant_id")
        participant = _find_participant(session, event.participant_id)
        participant.screen_share_events.append(event.timestamp)
        display_name = participant.display_name
        details = "screen share event"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported event type '{event.type}'")

    session.current_time = event.timestamp
    session.event_log.append(
        SessionEventEntry(
            timestamp=event.timestamp,
            type=event.type,
            participant_id=event.participant_id,
            display_name=display_name,
            details=details,
        )
    )
    output: ArbitratorOutput | None = None
    if session.participants:
        output = orchestrator.evaluate(session)
        session.prior_probabilities = output.candidate_probabilities
        session.confidence_history.append(
            ConfidenceHistoryEntry(
                timestamp=event.timestamp,
                probabilities=output.candidate_probabilities,
            )
        )
    store.update(session)

    if output is not None:
        await ws_manager.broadcast(
            session_id,
            {
                "type": "candidate_update",
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

    return {"status": "processed", "event_type": event.type}


@router.get("/{session_id}/confidence-history")
def get_confidence_history(
    session_id: str,
    store: InMemorySessionStore = Depends(get_store),
) -> dict[str, object]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": session_id,
        "history": [entry.model_dump(mode="json") for entry in session.confidence_history],
    }


@router.post("/{session_id}/feedback")
def submit_feedback(
    session_id: str,
    feedback: FeedbackRequest,
    store: InMemorySessionStore = Depends(get_store),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> dict[str, object]:
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    session.correct_candidate_id = feedback.correct_candidate_id
    store.update(session)
    orchestrator.invalidate_cache(session_id)

    output = orchestrator.evaluate(session)

    new_weights = adapt_weights_from_feedback(
        session_id=session_id,
        agents=orchestrator.agents,
        evidence=output.evidence,
        correct_candidate_id=feedback.correct_candidate_id,
    )

    for agent in orchestrator.agents:
        if agent.name in new_weights:
            agent._weight_override = new_weights[agent.name]

    logger.info(
        "feedback_applied",
        session_id=session_id,
        correct_candidate_id=feedback.correct_candidate_id,
        new_weights=new_weights,
    )

    return {
        "status": "feedback_applied",
        "session_id": session_id,
        "correct_candidate_id": feedback.correct_candidate_id,
        "adapted_weights": new_weights,
    }
