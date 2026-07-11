from functools import lru_cache

from lynx.agents.behavioral import BehavioralAgent
from lynx.agents.face_consistency import FaceConsistencyAgent
from lynx.agents.llm_reasoning import LLMReasoningAgent
from lynx.agents.name_matcher import NameMatcherAgent
from lynx.agents.solo_window import SoloWindowAgent
from lynx.agents.temporal import TemporalAgent
from lynx.arbitrator.arbitrator import LogOddsArbitrator
from lynx.orchestrator import AgentOrchestrator
from lynx.store.memory_store import InMemorySessionStore


@lru_cache(maxsize=1)
def get_store() -> InMemorySessionStore:
    return InMemorySessionStore()


@lru_cache(maxsize=1)
def get_orchestrator() -> AgentOrchestrator:
    return AgentOrchestrator(
        agents=[
            NameMatcherAgent(),
            TemporalAgent(),
            BehavioralAgent(),
            SoloWindowAgent(),
            FaceConsistencyAgent(),
            LLMReasoningAgent(),
        ],
        arbitrator=LogOddsArbitrator(),
    )
