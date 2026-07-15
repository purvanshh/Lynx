from functools import lru_cache

import structlog

from lynx.agents.behavioral import BehavioralAgent
from lynx.agents.face_consistency import FaceConsistencyAgent
from lynx.agents.llm_reasoning import LLMReasoningAgent
from lynx.agents.name_matcher import NameMatcherAgent
from lynx.agents.plugin_loader import discover_plugins
from lynx.agents.screen_share import ScreenShareAgent
from lynx.agents.solo_window import SoloWindowAgent
from lynx.agents.temporal import TemporalAgent
from lynx.arbitrator.arbitrator import LogOddsArbitrator
from lynx.orchestrator import AgentOrchestrator
from lynx.store.memory_store import InMemorySessionStore

logger = structlog.get_logger(__name__)

BUILTIN_AGENTS = [
    NameMatcherAgent(),
    TemporalAgent(),
    BehavioralAgent(),
    SoloWindowAgent(),
    FaceConsistencyAgent(),
    LLMReasoningAgent(),
    ScreenShareAgent(),
]


@lru_cache(maxsize=1)
def get_store() -> InMemorySessionStore:
    return InMemorySessionStore()


@lru_cache(maxsize=1)
def get_orchestrator() -> AgentOrchestrator:
    agents = list(BUILTIN_AGENTS)
    plugin_agents = discover_plugins()
    agents.extend(plugin_agents)
    if plugin_agents:
        logger.info("plugins_registered", count=len(plugin_agents), names=[a.name for a in plugin_agents])
    return AgentOrchestrator(
        agents=agents,
        arbitrator=LogOddsArbitrator(),
    )
