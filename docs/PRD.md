# Lynx Candidate Identification System — Professional PRD

---

## 1. Executive Summary

**Lynx** is a real-time, multi-agent Bayesian fusion system that automatically identifies the interview candidate from a pool of video conference participants. It continuously evaluates evidence across six independent signal agents, fuses them through a weighted Bayesian arbitrator, and produces explainable confidence scores with natural language reasoning.

**Key Differentiator:** Not face recognition. Not audio fingerprinting. The edge is the **multi-agent evidence fusion architecture** and the **explainability layer** — every identification comes with a human-readable audit trail.

---

## 2. Problem Statement

During live interviews on Google Meet, Teams, or Zoom, Lynx's fraud detection pipeline needs to analyze only the candidate's video/audio streams. Today, candidate identification is manual and error-prone. The system must:

- Automatically identify the correct participant with high confidence
- Continuously update confidence as new evidence arrives
- Explain *why* a participant was selected, not just *who*
- Gracefully surface uncertainty rather than making wrong confident calls
- Handle broken, missing, or conflicting signals without crashing

---

## 3. Goals & Non-Goals

### 3.1 Goals

| # | Goal | Priority |
|---|------|----------|
| G1 | Automatically identify the interview candidate from participant pool | P0 |
| G2 | Continuously update confidence as new evidence arrives during session | P0 |
| G3 | Explain reasoning for every identification decision | P0 |
| G4 | Gracefully surface uncertainty rather than forcing wrong confident calls | P0 |
| G5 | Handle broken, missing, or conflicting signals without crashing | P0 |
| G6 | Evaluate accuracy across 7 predefined edge-case scenarios | P1 |
| G7 | Provide REST API + live dashboard for real-time monitoring | P1 |

### 3.2 Non-Goals

| # | Non-Goal | Rationale |
|---|----------|-----------|
| NG1 | Face recognition against external identity databases | Out of prototype scope; intra-session consistency only |
| NG2 | Deep audio fingerprinting or voice biometric matching | Audio used only as weak behavioral signal, not foundation |
| NG3 | Integration with actual Google Meet / Teams / Zoom APIs | Prototype uses simulated meeting data |
| NG4 | Multi-language transcript support | English-only for prototype |
| NG5 | Real-time audio diarization (speaker separation from raw audio) | Transcript is pre-attributed to speaker IDs |

---

## 4. Functional Requirements

### 4.1 System Inputs

#### 4.1.1 Participant Stream

| Field | Type | Description |
|-------|------|-------------|
| `participant_id` | string | Unique identifier for the participant |
| `display_name` | string | Name shown in the meeting UI |
| `join_timestamp` | ISO 8601 datetime | When participant joined the session |
| `leave_timestamp` | ISO 8601 datetime (nullable) | When participant left (null if still present) |
| `webcam_on` | boolean + timestamp | Whether webcam is active, with state change timestamps |
| `screen_share_events` | array of timestamps | When screen sharing started/stopped |
| `speaking_activity` | boolean per second | Second-by-second speaking detection |
| `speaking_duration_total` | float (seconds) | Cumulative speaking time |

#### 4.1.2 Audio Stream (per participant)

| Field | Type | Description |
|-------|------|-------------|
| `raw_audio` | bytes | For Voice Activity Detection (VAD) only; no deep analysis |

#### 4.1.3 Video Stream (per participant)

| Field | Type | Description |
|-------|------|-------------|
| `webcam_frames` | image array | Sampled frames for face detection |

#### 4.1.4 Transcript

| Field | Type | Description |
|-------|------|-------------|
| `speaker_id` | string | Maps to participant_id |
| `utterance` | string | Spoken text |
| `timestamp` | ISO 8601 datetime | When utterance occurred |

#### 4.1.5 External Metadata

| Field | Type | Description |
|-------|------|-------------|
| `candidate_name` | string | Full name from calendar invite |
| `candidate_email` | string | Email address from calendar invite |
| `interviewer_names` | string[] | List of expected interviewer names |
| `scheduled_start_time` | ISO 8601 datetime | Interview start time from calendar |
| `calendar_invite_text` | string | Raw calendar invite body text |

### 4.2 System Output

Per participant, continuously updated:

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
      "score": 0.3,
      "weight": 0.15,
      "reasoning": "Display name 'MacBook Pro' does not match candidate name 'Rahul Sharma'. Weak negative signal."
    },
    {
      "agent": "TemporalAgent",
      "score": 0.85,
      "weight": 0.2,
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
      "weight": 0.1,
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

### 4.3 Confidence Tiers

| Tier | Probability Range | Behavior |
|------|-------------------|----------|
| `HIGH` | ≥ 0.85 | Confidently identify as candidate |
| `MEDIUM` | 0.65 - 0.84 | Likely candidate, continue monitoring |
| `LOW` | 0.45 - 0.64 | Weak signal, do not commit |
| `UNCERTAIN` | < 0.45 | Surface ambiguity, flag for human review |

---

## 5. Agent Specifications

### 5.1 NameMatcher Agent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Fuzzy match display names against known candidate and interviewer names |
| **Weight** | 0.15 |
| **Input** | `display_name`, `candidate_name`, `candidate_email`, `interviewer_names` |
| **Output** | `score ∈ [0,1]`, `reasoning` string |

**Logic:**

1. Compute token sort ratio (RapidFuzz) between `display_name` and `candidate_name`
2. Also match against `candidate_email` prefix (before `@`)
3. Check if `display_name` appears in `interviewer_names` list -> strong negative signal
4. Generic names (`MacBook Pro`, `iPhone`, `Guest`, `Zoom User`) -> score 0.1, flagged as ambiguous

### 5.2 TemporalAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Join time relative to scheduled start is a strong behavioral prior |
| **Weight** | 0.20 |
| **Input** | `join_timestamp`, `scheduled_start_time` |
| **Output** | `score ∈ [0,1]`, `reasoning` string |

**Logic:**

1. Candidate typically joins within `[-5, +3]` minutes of scheduled start
2. Interviewers typically join slightly before or after scheduled time
3. Observers join late
4. Score peaks at exactly scheduled start time, decays with distance (Gaussian or linear decay)

### 5.3 BehavioralAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Candidate and interviewer have structurally different speaking patterns |
| **Weight** | 0.25 |
| **Input** | `speaking_activity`, `speaking_duration_total`, transcript utterances |
| **Output** | `score ∈ [0,1]`, `reasoning` string |

**Logic:**

1. **Candidate pattern:** longer burst responses, more silence between turns (thinking time)
2. **Interviewer pattern:** shorter, more frequent turns, more evenly distributed
3. Compute features:
   - `avg_utterance_duration` (seconds)
   - `turn_frequency` (turns per minute)
   - `silence_ratio` (fraction of time not speaking)
4. Score candidate likelihood based on these features against trained/empirical distributions

### 5.4 SoloWindowAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Solo presence before others join is a near-certain candidate signal |
| **Weight** | 0.25 (0.0 if no solo window - weight redistributed) |
| **Input** | `join_timestamp`, `leave_timestamp` of all participants |
| **Output** | `score ∈ [0,1]` or `None`, `reasoning` string |

**Logic:**

1. Detect windows where `participant_count == 1`
2. Duration of solo window increases signal strength (score -> 1.0 as duration increases)
3. If multiple participants join simultaneously, signal is weaker or absent
4. If no solo window exists for any participant, agent returns `None` for all

### 5.5 FaceConsistencyAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Verify single consistent human face throughout the session (not identity matching) |
| **Weight** | 0.10 (0.0 if all webcams off - weight redistributed) |
| **Input** | `webcam_frames`, `webcam_on` status |
| **Output** | `score ∈ [0,1]`, `reasoning` string |

**Logic:**

1. Use MediaPipe Face Detection on webcam frames (sample every 2 seconds)
2. Track whether face count stays at 1 throughout the session for this participant
3. Flag conditions:
   - No face detected for extended period
   - Multiple faces detected
   - Face disappears and reappears (possible switching)
4. Does NOT match against any external face database

### 5.6 LLMReasoningAgent

| Attribute | Value |
|-----------|-------|
| **Purpose** | Handle edge cases, synthesize cross-signal reasoning, produce natural language explanation |
| **Weight** | 0.05 |
| **Input** | Structured participant summary + transcript snippets |
| **Output** | `score ∈ [0,1]`, `reasoning` string |

**Logic:**

1. Feed structured summary (participant metadata, speaking stats, transcript excerpts) to GPT-4o-mini
2. Prompt: *"Based on this data, which participant is most likely the interview candidate? Explain your reasoning."*
3. Parse response for `participant_id` recommendation + confidence + explanation
4. Acts as a sanity check and explainability layer, not the primary signal
5. **Rate limit:** Fire maximum once every 60 seconds to control API costs

---

## 6. Arbitrator Specification

### 6.1 Fusion Pattern

**Log-odds linear pooling with prior retention.**

### 6.2 Algorithm

Each agent produces a probability score. The arbitrator converts these to log-odds, computes a weighted average against the current prior, and converts back to probability space. This preserves evidence accumulation, handles missing agents gracefully, and avoids the score-collapse problem of naive multiplicative blending.

**Per update cycle, for each participant `p`:**

#### Step 1: Determine Active Agents

An agent is active for participant `p` if it produced a score for `p` in this cycle.

#### Step 2: Global Weight Redistribution

If any agent produced no scores for any participant, its weight is redistributed proportionally among the remaining globally active agents.

#### Step 3: Compute Log-Odds

```python
epsilon = 1e-6

def log_odds(score: float) -> float:
    score = clamp(score, epsilon, 1 - epsilon)
    return log(score / (1 - score))

lo_prior(p) = log_odds(prior_probability[p])

for each active agent a:
    lo_a(p) = log_odds(agent_score[a][p])
```

### 6.3 Weight Redistribution

All participants share the same redistributed global weight basis so cross-participant comparisons remain valid.

**Example:** If `SoloWindowAgent` (0.25) is globally inactive, weights become:

- NameMatcher: 0.15 -> 0.20
- TemporalAgent: 0.20 -> 0.267
- BehavioralAgent: 0.25 -> 0.333
- FaceConsistencyAgent: 0.10 -> 0.133
- LLMReasoningAgent: 0.05 -> 0.067

### 6.4 Weighted Posterior Log-Odds

```python
W_active(p) = sum(weights[a] for a in active_agents_for_p)

lo_posterior(p) = (1 - W_active(p)) * lo_prior(p)
                + sum(weights[a] * lo_a(p) for a in active_agents_for_p)
```

Interpretation:

- `(1 - W_active)` is the prior retention factor
- If all agents are active, the prior is fully replaced by weighted agent opinions
- If only some agents are active for a participant, the remaining mass stays with the prior

### 6.5 Convert to Odds and Normalize

```python
odds_p = exp(lo_posterior(p))
posterior_p = odds_p / sum(odds_q for all q)
```

This enforces the exactly-one-candidate assumption across participants.

### 6.6 Full Pseudocode

```python
def update_participants(participants, agent_results, base_weights, prior_probs):
    epsilon = 1e-6

    globally_active = {
        name
        for name, scores in agent_results.items()
        if any(score is not None for score in scores.values())
    }

    if not globally_active:
        return prior_probs

    total_active = sum(base_weights[name] for name in globally_active)
    normalized_weights = {
        name: base_weights[name] / total_active
        for name in globally_active
    }

    def lo(probability):
        clamped = max(epsilon, min(1 - epsilon, probability))
        return math.log(clamped / (1 - clamped))

    odds = {}
    default_prior = 1.0 / len(participants)

    for participant_id in participants:
        prior = prior_probs.get(participant_id, default_prior)
        prior = max(epsilon, min(1 - epsilon, prior))
        lo_prior = lo(prior)

        weighted_lo_sum = 0.0
        weight_sum = 0.0

        for agent_name, scores in agent_results.items():
            if agent_name not in globally_active:
                continue

            score = scores.get(participant_id)
            if score is None:
                continue

            weight = normalized_weights[agent_name]
            weighted_lo_sum += weight * lo(score)
            weight_sum += weight

        lo_post = (1 - weight_sum) * lo_prior + weighted_lo_sum
        odds[participant_id] = math.exp(lo_post)

    total_odds = sum(odds.values())
    return {
        participant_id: odds[participant_id] / total_odds
        for participant_id in participants
    }
```

### 6.7 Key Properties

| Property | Behavior |
|----------|----------|
| **Score collapse immunity** | Log-odds space avoids the multiplicative collapse problem |
| **Missing-agent grace** | Silent agents are skipped and prior retention compensates |
| **Evidence accumulation** | Posterior from cycle `t` becomes prior for cycle `t+1` |
| **Extreme-score stability** | Clamping prevents `log(0)` and infinite odds |
| **Multi-class correctness** | Odds normalization keeps probabilities across participants summing to 1 |

### 6.8 Update Frequency

- **Periodic:** Every 30 seconds during live session
- **Event-driven:** Immediately on any participant event (join, leave, name change, webcam toggle)

### 6.9 Confidence Tiers

| Tier | Probability Range | Behavior |
|------|-------------------|----------|
| `HIGH` | ≥ 0.85 | Confidently identify as candidate |
| `MEDIUM` | 0.65 - 0.84 | Likely candidate, continue monitoring |
| `LOW` | 0.45 - 0.64 | Weak signal, do not commit |
| `UNCERTAIN` | < 0.45 | Surface ambiguity, flag for human review |

### 6.10 Why This Replaces the Old Pseudocode

The previous multiplicative update:

```python
posterior[p] *= (weight * score + (1 - weight) * prior[p])
```

causes score collapse as more agents fire and does not provide a clean multi-class normalization story. The log-odds formulation is more standard, more numerically stable, and easier to explain in terms of each agent's weighted contribution.

---

## 7. Uncertainty Handling Matrix

| Scenario | System Behavior |
|----------|-----------------|
| All participants have generic names | NameMatcher contributes near-zero; other agents carry the decision |
| No solo window exists | SoloWindowAgent weight redistributed to other agents |
| Candidate changes display name mid-session | NameMatcher re-runs; temporal and behavioral signals persist |
| Two participants have similar join times | TemporalAgent scores both similarly; BehavioralAgent becomes deciding signal |
| Confidence stays UNCERTAIN after 5 minutes | System flags for human review; surfaces top 2 candidates with reasoning |
| Webcam off for all participants | FaceConsistencyAgent disabled; weight redistributed |
| LLM API unavailable or rate-limited | Skip LLM agent; weight redistributed; log warning |

**Critical Rule:** The system **never forces a HIGH confidence output**. If evidence is genuinely ambiguous, it explicitly says so.

---

## 8. Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MOCK MEETING SIMULATOR                           │
│  (Scenario configs → real-time event emission on defined schedule)         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EVENT STREAM                                  │
│  (Participant join/leave, name changes, speaking events, frame samples)    │
└─────────────────────────────────────────────────────────────────────────────┘
        │                                          │
        ▼                                          ▼
┌──────────────────────┐              ┌──────────────────────────────────────┐
│   AGENT ORCHESTRATOR │              │     EXTERNAL METADATA STORE          │
│  ┌────────────────┐  │              │  • candidate_name                    │
│  │ NameMatcher    │  │              │  • candidate_email                   │
│  ├────────────────┤  │              │  • interviewer_names[]               │
│  │ TemporalAgent  │  │              │  • scheduled_start_time              │
│  ├────────────────┤  │              │  • calendar_invite_text              │
│  │ BehavioralAgent│  │              └──────────────────────────────────────┘
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
│                         BAYESIAN ARBITRATOR                                │
│  (Weighted fusion, dynamic redistribution, confidence tier assignment)     │
└─────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONFIDENCE STORE                                 │
│  (Per-participant, timestamped history, in-memory + JSON persistence)      │
└─────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REST API (FastAPI)                            │
│  • GET /session/{id}/participants                                          │
│  • GET /session/{id}/candidate                                             │
│  • GET /session/{id}/confidence-history                                    │
│  • GET /health                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD UI (React)                             │
│  (Live confidence updates, evidence breakdown, uncertainty flags)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **Language** | Python 3.11+ | Ecosystem, readability, rapid prototyping |
| **Agent Orchestration** | Custom Python (not LangGraph) | Simpler, more inspectable, no framework lock-in |
| **Fuzzy Matching** | RapidFuzz | Fast, accurate, token sort ratio support |
| **Face Detection** | MediaPipe | Lightweight, CPU-only, no GPU needed |
| **LLM** | OpenAI GPT-4o-mini via API | Strong reasoning quality with cost efficiency; configurable |
| **API Layer** | FastAPI | Async-native, auto-docs, familiar |
| **Frontend Dashboard** | React + TypeScript | Live confidence updates via WebSocket/SSE |
| **Mock Simulator** | Custom Python script | Simulates meeting events + streams on schedule |
| **Data Store** | In-memory dict + JSON files | Prototype scope; no DB overhead |

---

## 10. Mock Simulator Requirements

### 10.1 Purpose

Since the prototype does not integrate with real meeting APIs, the simulator must emit realistic meeting events in real time based on predefined scenario configurations.

### 10.2 Scenario Config Format (JSON)

```json
{
  "scenario_id": "generic_name",
  "scheduled_start_time": "2024-01-15T10:00:00Z",
  "candidate": {
    "participant_id": "p_001",
    "display_name": "MacBook Pro",
    "join_offset_seconds": -120,
    "speaking_pattern": "burst",
    "webcam_on": true
  },
  "interviewers": [...],
  "observers": [...],
  "transcript": [...]
}
```

### 10.3 Required Scenarios

| # | Scenario | Description | Edge Case Covered |
|---|----------|-------------|-------------------|
| S1 | **Happy Path** | Candidate joins with correct name, webcam on, solo window | Baseline |
| S2 | **Generic Device Name** | Candidate joins as `MacBook Pro` or `iPhone` | Name ambiguity |
| S3 | **Multiple Interviewers + Observers** | 2 interviewers + 1 observer join | Distinguishing from crowd |
| S4 | **Name Change Mid-Session** | Candidate changes display name after joining | Dynamic identity |
| S5 | **Interviewer Enters Candidate Name** | Interviewer accidentally uses candidate's name | False positive risk |
| S6 | **No Solo Window** | Everyone joins simultaneously | Missing strong signal |
| S7 | **Webcam Off Throughout** | No participant has webcam on | Missing face signal |

### 10.4 Simulator Behavior

- Emit events in real time according to defined schedule
- Support playback speed multiplier (e.g., `2x` for faster testing)
- Output events as JSON to stdout and/or WebSocket
- Log ground truth `correct_candidate_id` for evaluation

---

## 11. Evaluation Criteria

### 11.1 Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **Identification Accuracy** | Correct candidate identified at session end | ≥ 6/7 scenarios |
| **Time-to-Correct-ID** | Seconds from session start to first HIGH confidence correct call | < 120s for happy path |
| **Confidence at ID Point** | Probability score when candidate is first identified | ≥ 0.85 for happy path |
| **False Positive Rate** | Wrong participant flagged as HIGH confidence | 0% |
| **Uncertainty Flag Rate** | Scenarios where system correctly flags UNCERTAIN | ≥ 1 (S6 or S7) |

### 11.2 Measurement Protocol

- Evaluate at fixed timestamps: 30s, 60s, 120s, 300s from session start
- Compare system output against ground truth `correct_candidate_id`
- Record confidence tier, probability, and explanation quality

---

## 12. API Specification

### 12.1 Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/sessions` | Create new session with metadata |
| `GET` | `/sessions/{id}` | Get session status |
| `GET` | `/sessions/{id}/participants` | List all participants with current scores |
| `GET` | `/sessions/{id}/candidate` | Get current best candidate identification |
| `GET` | `/sessions/{id}/confidence-history` | Time-series of confidence scores per participant |
| `POST` | `/sessions/{id}/events` | Inject simulator event (for testing) |
| `GET` | `/health` | Service health check |

### 12.2 WebSocket

- `ws://host/sessions/{id}/ws` - Stream real-time confidence updates
- Pushes `candidate_update` messages on every event and `heartbeat_update` every 30 seconds

---

## 13. Repo Structure

```text
lynx-candidate-id/
├── README.md                          # Project overview, setup, run instructions
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Modern Python packaging
├── .env.example                       # Environment variable template
│
├── docs/
│   ├── PRD.md                         # This document
│   ├── ARCHITECTURE.md                # Detailed architecture decisions
│   └── API.md                         # API contract documentation
│
├── lynx/                              # Main application package
│   ├── __init__.py
│   ├── config.py                      # Settings, env vars, constants
│   │
│   ├── agents/                        # Individual signal agents
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract base class for all agents
│   │   ├── name_matcher.py            # NameMatcher Agent
│   │   ├── temporal.py                # TemporalAgent
│   │   ├── behavioral.py              # BehavioralAgent
│   │   ├── solo_window.py             # SoloWindowAgent
│   │   ├── face_consistency.py        # FaceConsistencyAgent
│   │   └── llm_reasoning.py           # LLMReasoningAgent
│   │
│   ├── arbitrator/                    # Bayesian fusion engine
│   │   ├── __init__.py
│   │   ├── arbitrator.py              # Core fusion logic
│   │   ├── weights.py                 # Weight definitions + redistribution
│   │   └── confidence.py              # Confidence tier classification
│   │
│   ├── models/                        # Pydantic data models
│   │   ├── __init__.py
│   │   ├── participant.py             # Participant data structures
│   │   ├── session.py                 # Session data structures
│   │   ├── evidence.py                # Evidence / agent output models
│   │   └── transcript.py              # Transcript data structures
│   │
│   ├── store/                         # In-memory + JSON persistence
│   │   ├── __init__.py
│   │   ├── memory_store.py            # In-memory session state
│   │   └── persistence.py             # JSON serialization / deserialization
│   │
│   ├── api/                           # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app factory
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── sessions.py            # Session CRUD endpoints
│   │   │   ├── participants.py        # Participant endpoints
│   │   │   └── health.py              # Health check
│   │   └── dependencies.py            # FastAPI dependencies
│   │
│   └── utils/                         # Shared utilities
│       ├── __init__.py
│       ├── logging.py                 # Structured logging
│       └── time.py                    # Time parsing / formatting
│
├── simulator/                         # Mock meeting simulator
│   ├── __init__.py
│   ├── main.py                        # Simulator CLI entry point
│   ├── scheduler.py                   # Event scheduling / emission
│   ├── scenarios/                     # Predefined scenario configs
│   │   ├── happy_path.json
│   │   ├── generic_name.json
│   │   ├── multiple_interviewers.json
│   │   ├── name_change.json
│   │   ├── interviewer_candidate_name.json
│   │   ├── no_solo_window.json
│   │   └── webcam_off.json
│   └── generators/                    # Data generators
│       ├── participants.py
│       ├── transcript.py
│       └── speaking_patterns.py
│
├── dashboard/                         # React frontend
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ConfidenceMeter.tsx    # Visual confidence indicator
│   │   │   ├── EvidencePanel.tsx      # Agent evidence breakdown
│   │   │   ├── ParticipantCard.tsx    # Per-participant summary
│   │   │   ├── SessionTimeline.tsx    # Event timeline visualization
│   │   │   └── UncertaintyBanner.tsx  # Ambiguity warning banner
│   │   ├── hooks/
│   │   │   └── useSession.ts          # Session data fetching hook
│   │   ├── types/
│   │   │   └── index.ts               # TypeScript interfaces
│   │   └── api/
│   │       └── client.ts              # API client
│   └── public/
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── conftest.py                    # Pytest fixtures
│   ├── unit/
│   │   ├── test_name_matcher.py
│   │   ├── test_temporal.py
│   │   ├── test_behavioral.py
│   │   ├── test_solo_window.py
│   │   ├── test_face_consistency.py
│   │   ├── test_arbitrator.py
│   │   └── test_weights.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_end_to_end.py
│   └── fixtures/                      # Test data
│       ├── participants.json
│       └── transcripts.json
│
├── scripts/                           # Utility scripts
│   ├── run_simulator.py               # Quick simulator launcher
│   ├── evaluate.py                    # Evaluation runner
│   └── seed_data.py                   # Generate sample data
│
└── .github/
    └── workflows/
        └── ci.yml                     # GitHub Actions CI
```

---

## 14. Development Plan (Day-by-Day)

| Day | Focus | Deliverables |
|-----|-------|--------------|
| **Day 1** | Project scaffold + models + store | Repo structure, Pydantic models, in-memory store, FastAPI skeleton |
| **Day 2** | Agents 1-3 (Name, Temporal, Behavioral) | Three agents with unit tests, arbitrator skeleton |
| **Day 3** | Agents 4-5 (SoloWindow, FaceConsistency) | SoloWindow + MediaPipe face detection, arbitrator fusion complete |
| **Day 4** | LLM Agent + Arbitrator polish | LLM integration, weight redistribution, confidence tiers, uncertainty handling |
| **Day 5** | Mock Simulator + Scenarios | All 7 scenarios implemented, simulator emitting real-time events |
| **Day 6** | Dashboard + API wiring | React dashboard with live updates, full API integration |
| **Day 7** | Evaluation + polish | Run evaluation suite, fix edge cases, README, demo video |

---

## 15. Production Roadmap

| Phase | Improvement | Effort |
|-------|-------------|--------|
| P1 | Replace mock simulator with Zoom/Meet webhook integration | Medium |
| P2 | Add voice embedding agent (resemblyzer / pyannote) once audio infra is stable | High |
| P3 | Replace in-memory store with Redis for multi-session scale | Low |
| P4 | Add feedback loop: interviewer confirms/corrects candidate -> update agent weights | Medium |
| P5 | Face recognition against pre-interview ID document photo | High |
| P6 | Multi-language transcript support | Medium |

---

## 16. Explicit Assumptions

| # | Assumption | Impact if Violated |
|---|------------|-------------------|
| A1 | Prototype runs on simulated meeting data, not live API streams | Cannot deploy to production without P1 |
| A2 | Exactly one candidate per session | Multi-candidate sessions require redesign |
| A3 | Transcript is pre-attributed to speaker IDs | Raw audio diarization would require additional pipeline |
| A4 | LLM agent is rate-limited to once per 60 seconds | Higher frequency increases cost; lower frequency reduces responsiveness |
| A5 | Face detection samples frames every 2 seconds, not continuous video | May miss brief face switches |
| A6 | English-only transcripts and names | Non-English names may reduce NameMatcher accuracy |
| A7 | In-memory data store is sufficient for prototype scope | Sessions are lost on restart; no persistence across deploys |

---

## 17. Success Criteria

The project is considered complete when:

1. All 6 agents are implemented and individually tested
2. Arbitrator correctly fuses scores with dynamic weight redistribution
3. All 7 simulator scenarios run successfully and produce expected outputs
4. System achieves ≥ 6/7 identification accuracy
5. Dashboard displays live confidence updates with evidence breakdown
6. System correctly flags uncertainty in ambiguous scenarios (`S6`, `S7`)
7. False positive rate = 0% (no wrong participant flagged HIGH)
8. Code is documented, tested, and ready for demo

*End of PRD*
