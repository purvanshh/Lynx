from datetime import datetime, timezone

from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.arbitrator import LogOddsArbitrator
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.participant import Participant
from lynx.models.session import SessionState
from lynx.orchestrator import AgentOrchestrator


class StubAgent(BaseAgent):
    def __init__(self, agent_name: str, scores: dict[str, float | None]) -> None:
        self._name = agent_name
        self._scores = scores

    @property
    def name(self) -> str:
        return self._name

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS[self.name]

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        _ = session
        score = self._scores[participant_id]
        if score is None:
            return None
        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=score,
            weight=self.weight,
            reasoning=f"{self.name} score for {participant_id}",
        )


def make_session() -> SessionState:
    return SessionState(
        session_id="session-1",
        participants=[
            Participant(participant_id="p1", display_name="One"),
            Participant(participant_id="p2", display_name="Two"),
        ],
        prior_probabilities={"p1": 0.6, "p2": 0.4},
    )


def test_orchestrator_collects_evidence_for_every_agent_participant_pair() -> None:
    orchestrator = AgentOrchestrator(
        agents=[
            StubAgent("NameMatcher", {"p1": 0.8, "p2": 0.2}),
            StubAgent("TemporalAgent", {"p1": 0.7, "p2": 0.3}),
        ],
        arbitrator=LogOddsArbitrator(),
    )

    output = orchestrator.evaluate(make_session())

    assert len(output.evidence["p1"]) == 2
    assert len(output.evidence["p2"]) == 2
    assert output.top_candidate_id == "p1"
    assert output.updated_at.tzinfo == timezone.utc


def test_orchestrator_redistributes_weights_when_agent_is_globally_inactive() -> None:
    orchestrator = AgentOrchestrator(
        agents=[
            StubAgent("NameMatcher", {"p1": 0.9, "p2": 0.1}),
            StubAgent("TemporalAgent", {"p1": None, "p2": None}),
        ],
        arbitrator=LogOddsArbitrator(),
    )

    output = orchestrator.evaluate(make_session())

    assert output.evidence["p1"][0].weight == 1.0
    assert output.evidence["p1"][1].weight == 0.0


def test_orchestrator_returns_prior_when_all_agents_inactive() -> None:
    orchestrator = AgentOrchestrator(
        agents=[
            StubAgent("SoloWindowAgent", {"p1": None, "p2": None}),
            StubAgent("FaceConsistencyAgent", {"p1": None, "p2": None}),
        ],
        arbitrator=LogOddsArbitrator(),
    )

    output = orchestrator.evaluate(make_session())

    assert output.candidate_probabilities == {"p1": 0.6, "p2": 0.4}
    assert output.arbitrator_explanation == "No active agents produced evidence. Returning prior probabilities."


def test_orchestrator_handles_empty_participants_gracefully() -> None:
    orchestrator = AgentOrchestrator(agents=[], arbitrator=LogOddsArbitrator())

    output = orchestrator.evaluate(
        SessionState(
            session_id="empty-session",
            participants=[],
            prior_probabilities={},
        )
    )

    assert output.candidate_probabilities == {}
    assert output.top_candidate_id is None
