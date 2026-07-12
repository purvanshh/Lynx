# Lynx Architecture

## Overview

Lynx is a real-time multi-agent Bayesian fusion system that identifies the interview candidate from a pool of video conference participants. This document describes the architecture, data flow, component interactions, and key design decisions.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MOCK MEETING SIMULATOR                              │
│  (Scenario configs → real-time event emission at configurable speed)       │
│  simulator/scheduler.py  simulator/main.py  simulator/scenarios/*.json     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             EVENT STREAM                                    │
│  Participant join/leave, name changes, transcript utterances,               │
│  speaking activity, webcam frame samples                                    │
│  POST /sessions/{id}/events → lynx/api/routes/sessions.py                  │
└─────────────────────────────────────────────────────────────────────────────┘
        │                                          │
        ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────────────────┐
│   AGENT ORCHESTRATOR │              │     EXTERNAL METADATA               │
│  lynx/orchestrator.py│              │  • candidate_name                   │
│  ┌────────────────┐  │              │  • candidate_email                  │
│  │ NameMatcher    │  │              │  • interviewer_names[]              │
│  ├────────────────┤  │              │  • scheduled_start_time             │
│  │ TemporalAgent  │  │              └──────────────────────────────────────┘
│  ├────────────────┤  │
│  │ BehavioralAgent│  │
│  ├────────────────┤  │
│  │ SoloWindowAgent│  │
│  ├────────────────┤  │
│  │ FaceConsistency│  │
│  ├────────────────┤  │
│  │ LLMReasoning   │  │
│  └────────────────┘  │
└──────────┬───────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BAYESIAN ARBITRATOR                                  │
│  Log-odds linear pooling with prior retention                              │
│  Weight redistribution for globally inactive agents                        │
│  Confidence tier assignment (HIGH/MEDIUM/LOW/UNCERTAIN)                    │
│  lynx/arbitrator/arbitrator.py  lynx/arbitrator/weights.py                 │
│  lynx/arbitrator/confidence.py                                              │
└─────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONFIDENCE STORE                                   │
│  In-memory session state with timestamped probability history              │
│  Event-driven updates (every event triggers re-evaluation)                 │
│  lynx/store/memory_store.py                                                │
└─────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             REST API (FastAPI)                              │
│  POST   /sessions                         — Create session                 │
│  GET    /sessions/{id}                    — Get session state              │
│  GET    /sessions/{id}/participants       — List participants              │
│  GET    /sessions/{id}/candidate          — Get top candidate + evidence   │
│  GET    /sessions/{id}/confidence-history — Probability time series        │
│  POST   /sessions/{id}/events             — Inject events                  │
│  GET    /health                           — Health check                   │
│  lynx/api/main.py  lynx/api/routes/*.py  lynx/api/schemas.py              │
└─────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DASHBOARD UI (React + TypeScript)                  │
│  ConfidenceMeter, EvidencePanel, ParticipantCard, SessionTimeline,         │
│  UncertaintyBanner — polls API every 5 seconds                             │
│  dashboard/src/                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Session Creation
A session is created via `POST /sessions` with candidate metadata (name, email, interviewers, scheduled time). This initializes a `SessionState` with empty participant list and uniform prior probabilities.

### 2. Event Injection
Events arrive via `POST /sessions/{id}/events`. Supported event types:

| Event Type | Effect |
|------------|--------|
| `participant_join` | Adds participant with display name, join timestamp, webcam state |
| `participant_leave` | Sets participant's leave timestamp |
| `name_change` | Updates participant's display name |
| `transcript` | Appends utterance with speaker ID, text, timestamp, duration |
| `speaking_activity` | Extends speaking_activity boolean array per participant |
| `webcam_frame` | Adds sampled frame metadata (face count, image path) |

Each event triggers immediate re-evaluation through the full pipeline.

### 3. Orchestration
`AgentOrchestrator.evaluate()` iterates all 6 agents in fixed order, calling each agent's `evaluate()` for every participant. Results are collected as `agent_name → participant_id → AgentResult | None`. Globally inactive agents (None for all participants) are identified.

### 4. Agent Evaluation
Each agent independently produces a score `∈ [0, 1]` and a natural-language reasoning string.

- **NameMatcher** — Fuzzy matches display name against candidate name/email, checks interviewer negative list and generic name set
- **TemporalAgent** — Gaussian peak at scheduled start time with `[-5, +3]` minute window, capped at 0.9 to prevent log-odds dominance
- **BehavioralAgent** — Analyzes utterance duration, turn frequency, and silence ratio
- **SoloWindowAgent** — Detects periods with exactly one participant; duration-based scoring
- **FaceConsistencyAgent** — MediaPipe face detection on sampled frames; tracks consistency, flags multi-face and absence
- **LLMReasoningAgent** — OpenAI-compatible LLM call for cross-signal synthesis; 60-second rate limit

### 5. Arbitration
The arbitrator fuses agent scores using **log-odds linear pooling**:

1. Determine globally active agents (those with at least one non-None score)
2. Redistribute weights of inactive agents proportionally among active ones
3. For each participant, convert prior and agent scores to log-odds:
   `lo(p) = ln(p / (1-p))`
4. Compute posterior log-odds:
   `lo_posterior = (1 - W_active) × lo_prior + Σ(wa × lo_a)`
5. Convert back to probability space and normalize across participants
6. Assign confidence tier (HIGH ≥ 0.85, MEDIUM ≥ 0.65, LOW ≥ 0.45, UNCERTAIN < 0.45)

The posterior becomes the prior for the next update cycle, enabling evidence accumulation over time.

### 6. Response
The API returns the `ArbitratorOutput` including:
- Top candidate identification
- Full evidence array with per-agent scores, weights, and reasoning
- Arbitrator explanation string
- Confidence tier

### 7. Dashboard Display
The React dashboard polls the API every 5 seconds, rendering live:
- Confidence meter (color-coded gauge)
- Evidence panel (agent breakdown sorted by weight)
- Participant cards (per-participant probability and evidence)
- Session timeline (chronological event log)
- Uncertainty banner (shown when tier is UNCERTAIN)

---

## Agent Weight Rationale

| Agent | Weight | Rationale |
|-------|--------|-----------|
| **BehavioralAgent** | 0.25 | Highest weight because speaking patterns are the most reliable differentiator between candidate and interviewer. Candidates speak in bursts; interviewers speak uniformly. |
| **SoloWindowAgent** | 0.25 | Solo presence is a near-certain signal when present. Weight drops to 0 and redistributes when no solo window exists for any participant. |
| **TemporalAgent** | 0.20 | Join time is a strong but not definitive signal. Both candidates and interviewers may join near the scheduled start. Capped at 0.9 to prevent log-odds dominance. |
| **NameMatcher** | 0.15 | Useful when display name matches candidate name, but easily spoofed by generic device names or interviewer name collisions. |
| **FaceConsistencyAgent** | 0.10 | Intra-session consistency is supportive but not definitive. Webcam can be off or unreliable. |
| **LLMReasoningAgent** | 0.05 | Acts as a sanity check and explainability layer. Rate-limited; not a primary signal source. |

---

## Key Design Decisions

### Why Log-Odds Instead of Multiplicative Blending
The original pseudocode used multiplicative update: `posterior *= (weight × score + (1 - weight) × prior)`. This causes score collapse as more agents fire and lacks a clean multi-class normalization. Log-odds linear pooling is numerically stable, handles missing agents via prior retention, and provides proper multi-class normalization via odds summation.

### Why Custom Orchestration Instead of LangGraph
A custom Python orchestrator is simpler (~100 lines), fully inspectable, and has no external framework dependency. The pipeline is deterministic (agents run in fixed order) which aids debugging and testing.

### Why MediaPipe Instead of Deep Learning Face Models
MediaPipe Face Detection runs on CPU at real-time speeds with no GPU dependency. It provides binary face presence/absence detection without requiring identity matching, which aligns with the PRD's explicit non-goal of face recognition.

### Why RapidFuzz Instead of Standard Levenshtein
RapidFuzz's `token_sort_ratio` handles multi-word name comparisons better than simple Levenshtein distance. It correctly matches "Sharma, Rahul" to "Rahul Sharma" by sorting tokens alphabetically before comparison.

### Why the Temporal Score Cap (0.9)
The raw Gaussian peaks at exactly 1.0 for a participant joining precisely at the scheduled start. In log-odds space with ε=1e-6, this produces a log-odds of ~13.8, which when weighted by 0.20 contributes 2.76 to the posterior log-odds sum — dominating all other signals. The 0.9 cap reduces this to log-odds of 2.20 (weighted contribution 0.44), which is proportionate while still rewarding on-time joins.

---

## Confidence Tiers

| Tier | Range | Behavior |
|------|-------|----------|
| HIGH | ≥ 0.85 | Confident candidate identification |
| MEDIUM | 0.65 – 0.84 | Likely candidate, continue monitoring |
| LOW | 0.45 – 0.64 | Weak signal, do not commit |
| UNCERTAIN | < 0.45 | Surface ambiguity, flag for human review |

---

## Evaluation Framework

The evaluation script (`scripts/evaluate.py`) runs all 7 predefined scenarios against the API (in-process or via HTTP) and measures:

- **Identification Accuracy** — Correct candidate at session end (target: ≥ 6/7)
- **Time-to-Correct-ID** — Seconds to first HIGH confidence correct call (target: < 120s happy path)
- **Confidence at ID Point** — Probability score at identification (target: ≥ 0.85 happy path)
- **False Positive Rate** — Wrong participant flagged HIGH (target: 0%)
- **Uncertainty Flag Rate** — Correct UNCERTAIN flags in ambiguous scenarios (target: ≥ 1)

Scenarios are evaluated at fixed checkpoints: 30s, 60s, 120s, 300s from session start, plus the final event offset.

---

## Project Structure

```
lynx/
├── lynx/                          # Backend application
│   ├── agents/                    # 6 signal agents
│   ├── api/                       # FastAPI routes and schemas
│   ├── arbitrator/                # Log-odds fusion engine
│   ├── models/                    # Pydantic domain models
│   ├── store/                     # Session storage
│   └── utils/                     # Shared utilities
├── simulator/                     # Scenario playback engine
│   ├── scheduler.py               # Event scheduling
│   ├── main.py                    # CLI entry point
│   └── scenarios/                 # 7 edge-case scenarios
├── dashboard/                     # React + TypeScript frontend
├── tests/                         # Unit + integration tests
│   ├── unit/                      # 48 tests across all modules
│   └── integration/               # 6 tests covering API + E2E
├── scripts/                       # Evaluation and utility scripts
└── docs/                          # Documentation
```
