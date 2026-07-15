# Plugin Architecture

Lynx supports dynamic agent registration via a `plugins/` directory. Drop a Python
file into `plugins/`, restart the API, and the agent appears in the evidence array
without any code changes.

## How It Works

1. On startup, `lynx/agents/plugin_loader.py` scans `plugins/*.py`
2. Each file is imported and inspected for classes inheriting from `BaseAgent`
3. Validated agents are appended to the orchestrator's agent list
4. The agent's `name` and `weight` are used in log-odds fusion

## Build Your First Agent in 10 Minutes

### 1. Create the plugin file

```python
# plugins/my_agent.py
from lynx.agents.base import AgentResult, BaseAgent
from lynx.arbitrator.weights import DEFAULT_AGENT_WEIGHTS
from lynx.models.session import SessionState


class MyAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "MyAgent"

    @property
    def weight(self) -> float:
        return DEFAULT_AGENT_WEIGHTS.get(self.name, 0.08)

    def evaluate(self, session: SessionState, participant_id: str) -> AgentResult | None:
        # Return None if the agent cannot produce a score
        # Return AgentResult with a score in [0.0, 1.0]
        return AgentResult(
            agent=self.name,
            participant_id=participant_id,
            score=0.75,
            weight=self.weight,
            reasoning="Custom heuristic description.",
        )
```

### 2. (Optional) Register a default weight

Add your agent's weight to `DEFAULT_AGENT_WEIGHTS` in `lynx/arbitrator/weights.py`.
If omitted, the agent uses the fallback (0.05).

### 3. Restart

```bash
docker compose restart api
```

The agent appears in `evidence` responses under its `name`.

## Example Plugin

See `plugins/engagement_agent.py` for a complete working example that measures
speaking engagement ratio.

## API Contract

| Requirement | Specification |
|-------------|---------------|
| **Inheritance** | Must extend `lynx.agents.base.BaseAgent` |
| **name** | Non-empty string, unique among agents |
| **weight** | Float, typically 0.02–0.50 |

## Validation

The plugin loader validates each agent:
- `name` must be a non-empty string
- `evaluate()` must be callable
- Must inherit from `BaseAgent`

Failed plugins are logged as warnings (not fatal).
