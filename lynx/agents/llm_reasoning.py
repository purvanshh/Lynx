from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.config import Settings, get_settings
from lynx.models.session import SessionState
from lynx.utils.time import utc_now


class LLMReasoningAgent(BaseAgent):
    def __init__(
        self,
        settings: Settings | None = None,
        now_provider: Callable[[], datetime] | None = None,
        transport: Callable[[str], dict[str, object]] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.now_provider = now_provider or utc_now
        self.transport = transport or self._call_llm
        self.last_call_time: datetime | None = None
        self._session_cache: dict[str, dict[str, AgentResult]] = {}

    @property
    def name(self) -> str:
        return "LLMReasoningAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult:
        cached_results = self._session_cache.get(session.session_id)
        if cached_results is None or set(cached_results) != {
            participant.participant_id for participant in session.participants
        }:
            self._session_cache[session.session_id] = self._evaluate_session(session)
        return self._session_cache[session.session_id][participant_id]

    def _evaluate_session(self, session: SessionState) -> dict[str, AgentResult]:
        participant_ids = [participant.participant_id for participant in session.participants]
        now = self.now_provider()

        if not self.settings.llm_enabled:
            return self._neutral_results(session, "LLM analysis disabled in configuration.")
        if self.last_call_time is not None:
            elapsed = (now - self.last_call_time).total_seconds()
            if elapsed < self.settings.llm_rate_limit_seconds:
                return self._neutral_results(
                    session,
                    f"LLM rate limit active. Reusing neutral output until {self.settings.llm_rate_limit_seconds}s have elapsed.",
                )
        if not self.settings.llm_api_key:
            return self._neutral_results(session, "LLM API key not configured. Returning neutral reasoning signal.")
        if not participant_ids:
            return {}

        prompt = self._build_prompt(session)
        try:
            llm_payload = self.transport(prompt)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            return self._neutral_results(session, f"LLM request failed: {exc}. Returning neutral reasoning signal.")

        candidate_id = llm_payload["participant_id"]
        confidence = float(llm_payload["confidence"])
        explanation = str(llm_payload["explanation"]).strip()
        if candidate_id not in participant_ids:
            return self._neutral_results(
                session,
                f"LLM returned unknown participant '{candidate_id}'. Returning neutral reasoning signal.",
            )

        self.last_call_time = now
        confidence = max(0.0, min(1.0, confidence))
        non_candidate_score = 0.0
        if len(participant_ids) > 1:
            non_candidate_score = (1.0 - confidence) / (len(participant_ids) - 1)

        results: dict[str, AgentResult] = {}
        for current_participant_id in participant_ids:
            score = confidence if current_participant_id == candidate_id else non_candidate_score
            reasoning = explanation
            if current_participant_id != candidate_id:
                reasoning = (
                    f"LLM favored participant '{candidate_id}' over '{current_participant_id}'. {explanation}"
                )
            results[current_participant_id] = AgentResult(
                agent=self.name,
                participant_id=current_participant_id,
                score=round(score, 3),
                weight=self.weight,
                reasoning=reasoning,
            )
        return results

    def _neutral_results(self, session: SessionState, reasoning: str) -> dict[str, AgentResult]:
        return {
            participant.participant_id: AgentResult(
                agent=self.name,
                participant_id=participant.participant_id,
                score=0.5,
                weight=self.weight,
                reasoning=reasoning,
            )
            for participant in session.participants
        }

    def _build_prompt(self, session: SessionState) -> str:
        transcript_excerpt = "\n".join(
            f"- {utterance.speaker_id}: {utterance.utterance}"
            for utterance in session.transcript[:8]
        )
        participant_lines = "\n".join(
            (
                f"- {participant.participant_id}: name='{participant.display_name}', "
                f"joined='{participant.join_timestamp}', webcam_on={participant.webcam_on}, "
                f"speaking_duration_total={participant.speaking_duration_total}"
            )
            for participant in session.participants
        )
        return (
            "You are analyzing a live interview session to identify the likely candidate.\n"
            "Return strict JSON with keys participant_id, confidence, explanation.\n\n"
            f"Candidate name: {session.candidate_name}\n"
            f"Candidate email: {session.candidate_email}\n"
            f"Interviewers: {session.interviewer_names}\n"
            f"Scheduled start: {session.scheduled_start_time}\n"
            f"Participants:\n{participant_lines}\n\n"
            f"Transcript excerpt:\n{transcript_excerpt or '- No transcript available'}\n"
        )

    def _call_llm(self, prompt: str) -> dict[str, object]:
        body = {
            "model": self.settings.llm_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert interview analyst. Identify the likely candidate and explain why."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        request = Request(
            self.settings.llm_api_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.settings.llm_request_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))

        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return {
            "participant_id": parsed["participant_id"],
            "confidence": parsed["confidence"],
            "explanation": parsed["explanation"],
        }
