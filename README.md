# Lynx Candidate Identification System

Lynx is a real-time, multi-agent Bayesian fusion system that automatically identifies the interview candidate from a pool of video conference participants. It continuously evaluates evidence across seven independent signal agents (plus dynamically loaded plugins), fuses them through a weighted log-odds arbitrator, and produces explainable confidence scores with a full human-readable audit trail for every identification decision.

During a live interview on Google Meet, Teams, or Zoom, Lynx answers a single operational question with precision: *Which participant is the candidate right now, and why?*

---

## What Lynx Does

Lynx ingests live session events — participant joins, display name changes, speaking activity, transcript utterances, and sampled webcam frames — and maintains a continuously updated candidate probability for every participant in the room. It does not rely on any single signal. Instead, it treats candidate identification as an evidence fusion problem: multiple lightweight agents each produce a scored opinion, and a central arbitrator blends those opinions into a calibrated posterior probability.

The system explains every decision. When Lynx identifies a participant as the candidate, it surfaces the exact evidence that led to that conclusion — which agents fired, what they observed, how heavily they were weighted, and what reasoning they provided. When the evidence is ambiguous, Lynx explicitly flags uncertainty rather than forcing a wrong confident call.

---

## Core Capabilities

### Multi-Agent Evidence Fusion

Lynx runs seven built-in signal agents against every participant in a session, plus any plugins dropped into `plugins/`:

| Agent | Signal | Weight |
|-------|--------|--------|
| **NameMatcher** | Fuzzy match of display name against candidate name, email prefix, and interviewer negative list | 0.15 |
| **Temporal** | Join time relative to scheduled start — candidates join within a tight window | 0.18 |
| **Behavioral** | Speaking pattern analysis — burst responses vs. uniform interviewer turns | 0.22 |
| **SoloWindow** | Detection of solo presence before others join — a near-certain candidate signal | 0.22 |
| **FaceConsistency** | Intra-session face consistency via MediaPipe — single face, no switching | 0.08 |
| **LLMReasoning** | Cross-signal synthesis and edge-case reasoning via GPT-4o-mini | 0.05 |
| **ScreenShare** | Screen sharing events — candidates share their screen more frequently | 0.10 |
| *Plugin agents* | Dynamically loaded from `plugins/*.py` | Configurable |

Each agent returns a probability score and a natural language reasoning string. The system handles missing signals gracefully: if an agent cannot produce a score for any participant — for example, when no solo window exists or all webcams are off — its weight is automatically redistributed across the remaining active agents.

### Bayesian Log-Odds Arbitrator

The central arbitrator fuses agent opinions using log-odds linear pooling with prior retention. This is a mathematically standard ensemble method that avoids the score-collapse problem of naive multiplicative blending. The arbitrator:

- Converts agent scores and the current prior into log-odds space
- Computes a weighted average, retaining a fraction of the prior proportional to inactive agent weight
- Converts back to odds and normalizes across all participants
- Iterates: the posterior from one cycle becomes the prior for the next

Update cycles fire immediately on any participant event and on a 30-second periodic heartbeat. Results are pushed to connected WebSocket clients in real time.

### Confidence Tiers & Uncertainty Handling

Lynx surfaces four confidence tiers:

| Tier | Range | Behavior |
|------|-------|----------|
| **HIGH** | ≥ 0.85 | Confident candidate identification |
| **MEDIUM** | 0.65 – 0.84 | Likely candidate, monitoring continues |
| **LOW** | 0.45 – 0.64 | Weak signal, no commitment |
| **UNCERTAIN** | < 0.45 | Explicit ambiguity flag, human review recommended |

The system never forces a HIGH confidence output. If evidence is genuinely ambiguous — for instance, when all participants have generic device names and join simultaneously — Lynx flags the top two candidates with reasoning and requests human review.

### Real-Time Session API

Lynx exposes a complete FastAPI surface for session lifecycle and live evaluation:

- `POST /sessions` — Create a session with candidate metadata, interviewer names, and scheduled start time
- `GET /sessions/{id}` — Retrieve full session state
- `GET /sessions/{id}/participants` — List all participants with current scores
- `POST /sessions/{id}/events` — Inject live events: participant joins, leaves, name changes, transcript utterances, speaking activity, webcam frames
- `GET /sessions/{id}/candidate` — Get the current top candidate with full evidence array, confidence tier, and arbitrator explanation
- `GET /sessions/{id}/confidence-history` — Time-series of probability evolution per participant
- `POST /sessions/{id}/feedback` — Human feedback to correct/confirm identification; adapts agent weights via EMA
- `GET /sessions/{id}/anomalies` — Recent anomaly alerts (confidence drops, face drops, dual candidates, oscillation)
- `WS /sessions/{id}/ws` — Stream real-time candidate updates, heartbeat messages, and anomaly alerts
- `GET /analytics/summary` — Aggregate metrics across all sessions (tier distribution, confidence histogram, agent activation)
- `GET /metrics` — Prometheus scrape endpoint
- `GET /health` — Service health check

Event injection and a background 30-second heartbeat both trigger re-evaluation: orchestrator → agents → arbitrator → updated confidence store. Results are broadcast to all WebSocket clients connected to the session.

### Mock Meeting Simulator

The simulator loads scenario configurations and emits timed events in real time, driving the API exactly as a live meeting would. It supports playback speed multipliers — run a 30-minute interview at 5× speed for rapid testing.

Seven predefined scenarios cover the full edge-case matrix:

1. **Happy Path** — Candidate joins with correct name, webcam on, and a strong solo window
2. **Generic Device Name** — Candidate appears as "MacBook Pro", forcing non-name evidence to carry
3. **Multiple Interviewers + Observers** — Distinguishing the candidate from a crowded room
4. **Name Change Mid-Session** — Candidate updates display name after joining, triggering a confidence shift
5. **Interviewer Enters Candidate Name** — An interviewer shares the candidate's display name, testing false-positive resistance
6. **No Solo Window** — Everyone joins simultaneously, so SoloWindowAgent should drop out and redistribute weight
7. **Webcam Off Throughout** — No face-consistency signal is available, so the remaining agents must carry

Each scenario includes complete participant arrays, speaking patterns, transcript streams, join offsets, and ground truth labels for automated evaluation.

### Evaluation Framework

The evaluation runner executes all seven scenarios against the live API and measures:

- **Identification Accuracy** — Correct candidate identified at session end
- **Time-to-Correct-ID** — Seconds from start to first HIGH confidence correct call
- **Confidence at Identification** — Probability score at the moment of identification
- **False Positive Rate** — Wrong participant flagged as HIGH confidence
- **Uncertainty Flag Rate** — Correct ambiguity flags in ambiguous scenarios

Results are produced as a structured JSON report with pass/fail assertions against PRD targets.

### Live Dashboard

The React dashboard provides a real-time operational view of any active session:

- **Confidence Meter** — Color-coded gauge showing the top candidate's probability and tier
- **Evidence Panel** — Complete agent breakdown with scores, weights, and reasoning strings
- **Participant Cards** — Per-participant probability, evidence list, and webcam status
- **Session Timeline** — Chronological visualization of joins, leaves, speaking events, and transcript utterances
- **Uncertainty Banner** — Dynamic alert when confidence drops to UNCERTAIN, surfacing the top two candidates and recommending human review
- **Feedback Controls** — "Mark Correct / Mark Incorrect" buttons to confirm or correct identification, adapting agent weights in real time
- **Anomaly Alerts** — Real-time banners for confidence drops, face score drops, dual candidate detection, and oscillation

The dashboard polls the API every five seconds and optionally connects via WebSocket for push-based real-time updates.

### Multi-Session Analytics

The analytics dashboard provides cross-session operational intelligence:

- **Confidence Tier Breakdown** — Pie chart of HIGH / MEDIUM / LOW / UNCERTAIN distributions across all sessions
- **Confidence Histogram** — Bar chart showing the distribution of top-candidate probabilities
- **Agent Activation Heatmap** — Activity levels per agent across all sessions
- **Aggregate Metrics** — Total sessions, participants, events processed, and average confidence

### Human Feedback Loop

Lynx supports human-in-the-loop weight adaptation. When an operator confirms or corrects the system's identification:

1. `POST /sessions/{id}/feedback` receives the correct candidate ID
2. Agents that scored the correct candidate highly increase in weight; those that scored it lowly decrease
3. EMA update with α=0.15, clamped to [0.02, 0.50], then re-normalized
4. Adapted weights persist to `data/adapted_weights.json` and survive restarts

### Anomaly Detection & Observability

Lynx detects operational anomalies in real time:

- **Confidence Drop** — Warning when top-candidate probability drops by >0.3 between evaluations
- **Face Score Drop** — Face consistency score below 0.5 for the top candidate
- **Dual Candidate** — Multiple participants with candidate-like signals
- **Late Join** — Participant joins >180s after scheduled start
- **Confidence Oscillation** — Top candidate identity flip-flops across recent evaluations

Prometheus metrics expose evaluation latency, agent eval times, confidence tiers, and anomaly counts. A pre-built Grafana dashboard visualizes the full observability stack.

### Plugin Architecture

Lynx supports dynamic agent registration without code changes. Drop a Python file into `plugins/` that inherits from `BaseAgent`, restart the API, and the agent appears in the evidence array automatically.

See `docs/PLUGINS.md` for the "Build Your First Agent in 10 Minutes" tutorial.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MOCK MEETING SIMULATOR                     │
│         (Scenario configs → real-time event emission)         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        EVENT STREAM                           │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────┐      ┌──────────────────────────────────┐
│ AGENT ORCHESTRATOR│      │    EXTERNAL METADATA STORE       │
│  ┌────────────┐  │      │  • candidate_name                │
│  │ NameMatcher│  │      │  • candidate_email               │
│  ├────────────┤  │      │  • interviewer_names           │
│  │ Temporal   │  │      │  • scheduled_start_time          │
│  ├────────────┤  │      │  • calendar_invite_text          │
│  │ Behavioral │  │      └──────────────────────────────────┘
│  ├────────────┤  │
│  │ SoloWindow │  │
│  ├────────────┤  │
│  │ FaceConsistency│ │
│  ├────────────┤  │
│  │ LLMReasoning│  │
│  └────────────┘  │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                 BAYESIAN LOG-ODDS ARBITRATOR                  │
│      (Weighted fusion, dynamic redistribution,                │
│       prior retention, multi-class normalization)             │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                     CONFIDENCE STORE                          │
│         (Per-participant, timestamped probability history)    │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    REST API + WebSocket (FastAPI)              │
│         • Session management                                  │
│         • Event ingestion                                     │
│         • Candidate evaluation                                │
│         • Confidence history                                  │
│         • Real-time push via /sessions/{id}/ws                │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DASHBOARD UI (React)                        │
│         • Live confidence updates                             │
│         • Evidence breakdown                                  │
│         • Timeline visualization                              │
│         • Uncertainty alerts                                  │
└─────────────────────────────────────────────────────────────┘
```

Key architectural decisions:

- **Custom orchestration, not LangGraph** — Simpler, more inspectable, no framework lock-in
- **Log-odds fusion, not naive multiplication** — Prevents score collapse, mathematically sound multi-class extension
- **MediaPipe face detection** — Lightweight, CPU-only, no GPU dependency
- **RapidFuzz** — Fast token-sort ratio for name matching with typo and nickname tolerance
- **In-memory store with JSON persistence** — Sufficient for prototype scope; Redis-ready for production scale
- **WebSocket push** — Real-time candidate updates and 30-second heartbeat broadcast to connected clients

---

## Repository Structure

```
lynx/
├── lynx/                          # Backend application
│   ├── agents/                    # Signal agents (7 built-in + plugin loader)
│   │   ├── base.py                # Abstract BaseAgent
│   │   ├── plugin_loader.py       # Dynamic plugin discovery
│   │   ├── name_matcher.py
│   │   ├── temporal.py
│   │   ├── behavioral.py
│   │   ├── solo_window.py
│   │   ├── face_consistency.py
│   │   ├── llm_reasoning.py
│   │   └── screen_share.py
│   ├── api/                       # FastAPI routes, schemas, WebSocket, metrics
│   │   ├── main.py                # App factory, middleware, /metrics
│   │   ├── schemas.py             # Pydantic request/response schemas
│   │   ├── metrics.py             # Prometheus metric definitions
│   │   ├── anomaly.py             # Anomaly detection rules
│   │   ├── ws_manager.py          # WebSocket connection manager
│   │   └── routes/
│   │       ├── sessions.py        # Session CRUD + event injection + feedback
│   │       ├── participants.py    # Participant + candidate endpoints
│   │       ├── analytics.py       # Per-session anomaly endpoint
│   │       ├── analytics_summary.py  # Cross-session aggregate analytics
│   │       ├── ws.py              # WebSocket live stream endpoint
│   │       └── health.py          # Health check
│   ├── arbitrator/                # Log-odds fusion engine + weight adaptation
│   │   ├── arbitrator.py          # LogOddsArbitrator
│   │   ├── confidence.py          # Confidence tier classification
│   │   └── weights.py             # DEFAULT_AGENT_WEIGHTS + EMA feedback adaptation
│   ├── models/                    # Pydantic domain models
│   ├── store/                     # Session storage (in-memory + JSON persistence)
│   └── utils/                     # Logging, time helpers
│
├── plugins/                       # Drop-in agent plugins
│   └── engagement_agent.py        # Example plugin
│
├── simulator/                     # Scenario playback and scheduling
│   ├── scheduler.py
│   ├── main.py
│   └── scenarios/                 # 7 predefined edge-case scenarios
│
├── dashboard/                     # React + TypeScript frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnalyticsPage.tsx  # Cross-session analytics (Recharts)
│   │   │   ├── ConfidenceMeter.tsx
│   │   │   ├── EvidencePanel.tsx
│   │   │   ├── FeedbackControls.tsx  # Mark Correct / Incorrect
│   │   │   ├── ParticipantCard.tsx
│   │   │   ├── SessionTimeline.tsx
│   │   │   └── UncertaintyBanner.tsx
│   │   ├── hooks/
│   │   │   └── useSession.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   └── types/
│   │       └── index.ts
│
├── tests/                         # 74 unit + integration tests
│   ├── unit/
│   └── integration/
│
├── docs/                          # Documentation
│   ├── PRD.md, ARCHITECTURE.md, API.md
│   ├── FEEDBACK.md                # Human feedback loop reference
│   ├── PLUGINS.md                 # Plugin development tutorial
│   ├── PERFORMANCE.md             # Latency benchmark results
│   ├── ROBUSTNESS.md              # Noise injection results
│   └── SECURITY_AUDIT.md          # Adversarial attack resistance
│
├── scripts/                       # Development utilities
│   ├── run_simulator.py, evaluate.py, benchmark.py
│   ├── seed_data.py, stress_test.py, robustness_test.py
│   └── noise_injector.py
│
├── prometheus/                    # Prometheus scrape config
├── docker-compose.yml             # API + Dashboard + Prometheus + Grafana
├── Dockerfile                     # Multi-stage Python build
├── Makefile                       # dev, test, evaluate, benchmark, demo, prometheus
├── requirements.txt
└── pyproject.toml
```

---

## Quick Start

### Docker (Quickest)

```bash
git clone https://github.com/purvanshh/Lynx.git
cd Lynx
docker compose up --build
```

Open `http://localhost:3000` for the dashboard. The API is at `http://localhost:8000/docs`.

### Prerequisites (Manual)

- Python 3.11+
- Node.js 18+ (for dashboard)
- Docker & Docker Compose (optional, for observability stack)
- An OpenAI-compatible API key (optional, for LLMReasoningAgent)

### Environment Setup

```bash
cp .env.example .env
# Edit .env and add your LYNX_LLM_API_KEY if using the LLM agent
```

### Run the Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn lynx.api.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### Run the Dashboard

```bash
cd dashboard
npm install
npm run dev
```

The dashboard connects to the backend at `http://localhost:8000` and polls for live updates.

### Run a Scenario

```bash
python scripts/run_simulator.py simulator/scenarios/happy_path.json --speed 2.0
```

This loads the happy path scenario, emits events at 2× speed, and injects them into the running API.

### Run the Evaluation Suite

```bash
python scripts/evaluate.py
```

This executes all seven scenarios, measures identification accuracy, time-to-correct-ID, confidence scores, and false positive rates, and produces a structured evaluation report.

### Run Tests

```bash
pytest
```

The test suite covers all agents, the log-odds arbitrator, weight redistribution, the event scheduler, and end-to-end API flows (74 tests).

### Makefile Targets

```bash
make dev           # docker compose up
make test          # Run tests in Docker
make evaluate      # Run evaluation suite
make benchmark     # Run latency benchmarks
make demo          # Full stack + happy path simulator at 5x
make prometheus    # Start API + Prometheus + Grafana
make stress-test   # Adversarial attack resistance test
make robustness-test  # Noise injection robustness test
```

---

### WebSocket Live Stream

Connect to a session's WebSocket endpoint to receive push updates:

```bash
# Requires a WebSocket client like websocat or wscat
wscat -c ws://localhost:8000/sessions/{session_id}/ws
```

Messages arrive as JSON with a `type` field:

- `candidate_update` — sent immediately after every event injection
- `heartbeat_update` — sent every 30 seconds by the background heartbeat task

Both contain a `data` field with the same structure as the `/candidate` endpoint response.

---

## API Usage Example

### Create a Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_name": "Rahul Sharma",
    "candidate_email": "rahul.sharma@example.com",
    "interviewer_names": ["Alice Chen"],
    "scheduled_start_time": "2024-01-15T10:00:00Z"
  }'
```

### Inject a Participant Join Event

```bash
curl -X POST http://localhost:8000/sessions/{session_id}/events \
  -H "Content-Type: application/json" \
  -d '{
    "type": "participant_join",
    "participant_id": "p_001",
    "display_name": "MacBook Pro",
    "timestamp": "2024-01-15T09:58:00Z"
  }'
```

### Get the Current Candidate

```bash
curl http://localhost:8000/sessions/{session_id}/candidate
```

Response:

```json
{
  "participant_id": "p_001",
  "display_name": "MacBook Pro",
  "candidate_probability": 0.87,
  "is_candidate": true,
  "confidence_tier": "HIGH",
  "evidence": [
    {
      "agent": "NameMatcher",
      "score": 0.1,
      "weight": 0.15,
      "reasoning": "Generic device name 'MacBook Pro'. Ambiguous, weak signal."
    },
    {
      "agent": "TemporalAgent",
      "score": 0.85,
      "weight": 0.20,
      "reasoning": "Joined 2 minutes before scheduled start. Consistent with candidate behavior."
    },
    {
      "agent": "BehavioralAgent",
      "score": 0.91,
      "weight": 0.25,
      "reasoning": "Speaking pattern shows burst responses averaging 45s, consistent with answering interview questions."
    },
    {
      "agent": "SoloWindowAgent",
      "score": 1.0,
      "weight": 0.25,
      "reasoning": "Was the only participant in the room for 3 minutes before interviewer joined."
    },
    {
      "agent": "FaceConsistencyAgent",
      "score": 0.78,
      "weight": 0.10,
      "reasoning": "Single consistent face detected throughout session. No face switching detected."
    },
    {
      "agent": "LLMReasoningAgent",
      "score": 0.88,
      "weight": 0.05,
      "reasoning": "Transcript analysis: participant answers questions, uses first-person context about job application. Interviewer speech pattern absent."
    }
  ],
  "arbitrator_explanation": "Despite an unrecognized display name, this participant exhibits strong candidate behavioral signals: solo early join, burst speaking pattern, and consistent face. Confidence is HIGH.",
  "updated_at": "2024-01-15T10:23:45Z"
}
```

---

## Agent Details

### NameMatcher Agent

Matches display names against the candidate name and email prefix using RapidFuzz token-sort ratio. Handles typos, nicknames, and partial matches. Flags generic device names — "MacBook Pro", "iPhone", "Guest", "Zoom User" — as ambiguous with a fixed low score. Detects interviewer names as a strong negative signal.

### Temporal Agent

Scores join time relative to the scheduled start using a Gaussian peak at exactly `T=0` with a `[-5, +3]` minute window. Candidates who join right on time receive the highest score; early or late joins decay smoothly; joins outside the window score zero.

### Behavioral Agent

Analyzes speaking patterns from transcript utterances and second-by-second speaking activity. Computes average utterance duration, turn frequency, and silence ratio. Candidates speak in longer bursts with thinking-time gaps between turns; interviewers speak more uniformly and frequently.

### SoloWindow Agent

Detects periods where exactly one participant is present in the room. The longer the solo window, the stronger the candidate signal. If no solo window exists for any participant, the agent returns no signal and its weight is redistributed.

### FaceConsistency Agent

Samples webcam frames every two seconds and runs MediaPipe Face Detection. Tracks whether a single consistent face remains present throughout the session. Flags multiple faces, extended absence, and face switching — but does not match against any external identity database.

### LLM Reasoning Agent

Feeds structured participant summaries and recent transcript excerpts to GPT-4o-mini via OpenAI-compatible API. Asks for a participant recommendation, confidence score, and reasoning. Parses the structured JSON response and acts as a sanity-check layer. Rate-limited to once per 60 seconds to control API costs. Falls back to a local transcript heuristic when the API is unavailable or rate-limited.

---

## Evaluation & Metrics

The evaluation framework runs all seven scenarios and measures:

| Metric | Target | Current |
|--------|--------|---------|
| Identification Accuracy | ≥ 6/7 scenarios | **7/7 (100%)** |
| False Positive Rate | 0% | **0%** |
| Avg Time-to-Correct-ID | — | **30.0s** |
| Time-to-Correct-ID (happy path) | < 120 s | **30.0s** |
| Confidence at ID (happy path) | ≥ 0.85 | **0.997** |
| Confidence at ID (generic_name) | — | **0.928** |
| Confidence at ID (interviewer_candidate_name) | — | **LOW** (correctly withheld HIGH in ambiguous scenario) |

Scenarios are evaluated at fixed checkpoints — 30s, 60s, 120s, and 300s from session start — and compared against ground truth labels. Full results are in `output/evaluation_report.json`.

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.11 | Ecosystem, readability, rapid prototyping |
| API | FastAPI | Async-native, auto-generated OpenAPI docs, familiar |
| Agent Orchestration | Custom Python | Simpler, more inspectable than framework solutions |
| Weight Adaptation | EMA feedback loop | Human-in-the-loop continuous improvement |
| Fuzzy Matching | RapidFuzz | Fast, accurate token-sort ratio |
| Face Detection | MediaPipe | Lightweight, CPU-only, no GPU dependency |
| LLM | OpenAI GPT-4o-mini (configurable) | Strong reasoning with cost efficiency; OpenAI-compatible |
| Frontend | React + TypeScript + Recharts | Live updates, analytics charts, type safety |
| Testing | pytest (74 tests) | Unit, integration, and end-to-end coverage |
| Metrics | Prometheus + Grafana | Latency histograms, agent eval times, anomaly counts |
| Logging | structlog | Structured JSON logging with timestamps and context |
| Simulator | Custom Python + asyncio | Real-time event scheduling with speed control |
| Container | Docker + Docker Compose | Clone-and-run demo, 4-service stack |

---

## Core Documents

- **PRD** — Full product requirements: `docs/PRD.md`
- **Architecture** — Design decisions and data flow: `docs/ARCHITECTURE.md`
- **API** — Endpoint contracts and examples: `docs/API.md`
- **Feedback Loop** — Human-in-the-loop weight adaptation: `docs/FEEDBACK.md`
- **Plugins** — Build your own agent: `docs/PLUGINS.md`
- **Performance** — Latency benchmarks: `docs/PERFORMANCE.md`
- **Robustness** — Noise injection results: `docs/ROBUSTNESS.md`
- **Security** — Adversarial attack resistance: `docs/SECURITY_AUDIT.md`

---

## License

MIT License — see `LICENSE` for details.
