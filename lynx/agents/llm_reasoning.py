from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from rapidfuzz import fuzz

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
        if not participant_ids:
            return {}

        if not self.settings.llm_enabled:
            return self._heuristic_results(session, "LLM analysis disabled in configuration.")
        if self.last_call_time is not None:
            elapsed = (now - self.last_call_time).total_seconds()
            if elapsed < self.settings.llm_rate_limit_seconds:
                return self._heuristic_results(
                    session,
                    (
                        "LLM rate limit active. Falling back to the local transcript heuristic "
                        f"until {self.settings.llm_rate_limit_seconds}s have elapsed."
                    ),
                )
        if not self.settings.llm_api_key:
            return self._heuristic_results(
                session,
                "LLM API key not configured. Used the local transcript heuristic instead.",
            )

        prompt = self._build_prompt(session)
        try:
            llm_payload = self.transport(prompt)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
            return self._heuristic_results(
                session,
                f"LLM request failed: {exc}. Used the local transcript heuristic instead.",
            )

        candidate_id = llm_payload["participant_id"]
        confidence = float(str(llm_payload["confidence"]))
        explanation = str(llm_payload["explanation"]).strip()
        if candidate_id not in participant_ids:
            return self._heuristic_results(
                session,
                f"LLM returned unknown participant '{candidate_id}'. Used the local transcript heuristic instead.",
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

    def _heuristic_results(self, session: SessionState, fallback_reason: str) -> dict[str, AgentResult]:
        scored_participants = [
            self._score_participant(session, participant.participant_id)
            for participant in session.participants
        ]
        if not scored_participants:
            return {}

        best_score = max(score for _, score, _ in scored_participants)
        second_best_score = max(
            (score for _, score, _ in scored_participants if score != best_score),
            default=best_score,
        )
        confidence_boost = min(0.15, max(0.0, best_score - second_best_score) * 0.5)
        winner_score = min(0.92, best_score + confidence_boost)

        results: dict[str, AgentResult] = {}
        winner_id = max(scored_participants, key=lambda item: item[1])[0]
        for participant_id, score, reasoning in scored_participants:
            adjusted_score = winner_score if participant_id == winner_id else score
            if participant_id != winner_id:
                reasoning = f"{reasoning} Heuristic favored '{winner_id}' instead."
            results[participant_id] = AgentResult(
                agent=self.name,
                participant_id=participant_id,
                score=round(max(0.05, min(0.95, adjusted_score)), 3),
                weight=self.weight,
                reasoning=f"{fallback_reason} {reasoning}",
            )
        return results

    def _score_participant(self, session: SessionState, participant_id: str) -> tuple[str, float, str]:
        participant = next(
            p for p in session.participants if p.participant_id == participant_id
        )
        utterances = [utterance for utterance in session.transcript if utterance.speaker_id == participant_id]
        utterance_text = " ".join(utterance.utterance for utterance in utterances).lower()
        durations = [utterance.duration_seconds or 0.0 for utterance in utterances]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        total_duration = sum(durations)

        first_person_markers = len(re.findall(r"\b(i|i'm|i’ve|i've|my|me|we|our|us)\b", utterance_text))
        question_markers = utterance_text.count("?")
        interviewer_cues = sum(
            utterance_text.count(phrase)
            for phrase in (
                "can you",
                "could you",
                "tell me",
                "walk me through",
                "thanks for joining",
                "let's start",
                "how did you",
            )
        )
        candidate_name_mentions = 0
        if session.candidate_name:
            candidate_tokens = [
                token.lower()
                for token in session.candidate_name.split()
                if token.strip()
            ]
            candidate_name_mentions = sum(utterance_text.count(token) for token in candidate_tokens)

        interviewer_name_match = max(
            (
                fuzz.token_sort_ratio(participant.display_name.lower(), interviewer_name.strip().lower())
                for interviewer_name in session.interviewer_names
            ),
            default=0,
        )

        score = 0.5
        score += min(0.18, 0.05 * first_person_markers)
        score -= min(0.28, 0.10 * question_markers + 0.06 * interviewer_cues)
        score -= min(0.15, 0.04 * candidate_name_mentions) if question_markers or interviewer_cues else 0.0
        if avg_duration >= 25:
            score += 0.12
        elif avg_duration <= 8 and utterances:
            score -= 0.12
        if total_duration >= 70:
            score += 0.08
        if utterances and len(utterances) <= 2 and avg_duration >= 30:
            score += 0.04
        if interviewer_name_match > 80:
            score -= 0.30

        if session.scheduled_start_time is not None and participant.join_timestamp is not None:
            delta_minutes = (participant.join_timestamp - session.scheduled_start_time).total_seconds() / 60.0
            if delta_minutes < -0.5:
                score += 0.08
            elif delta_minutes > 0.5:
                score -= 0.08

        reasoning_parts = [
            f"heuristic score {score:.2f}",
            f"avg response {avg_duration:.1f}s",
            f"first-person markers {first_person_markers}",
        ]
        if question_markers or interviewer_cues:
            reasoning_parts.append(
                f"question/interviewer cues {question_markers + interviewer_cues}"
            )
        if interviewer_name_match > 80:
            reasoning_parts.append("display name resembles an interviewer")
        if session.scheduled_start_time is not None and participant.join_timestamp is not None:
            delta_minutes = (participant.join_timestamp - session.scheduled_start_time).total_seconds() / 60.0
            reasoning_parts.append(f"joined {delta_minutes:+.1f} min from start")

        return participant_id, max(0.05, min(0.95, score)), ". ".join(reasoning_parts) + "."

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
        parsed = self._parse_llm_content(content)
        return {
            "participant_id": parsed["participant_id"],
            "confidence": parsed["confidence"],
            "explanation": parsed["explanation"],
        }

    def _parse_llm_content(self, content: str) -> dict[str, object]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                cleaned = "\n".join(lines[1:-1]).strip()
                if cleaned.lower().startswith("json"):
                    cleaned = cleaned[4:].strip()
        parsed = json.loads(cleaned)
        return {
            "participant_id": parsed["participant_id"],
            "confidence": parsed["confidence"],
            "explanation": parsed["explanation"],
        }
