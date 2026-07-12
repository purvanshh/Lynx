# Lynx API Reference

Base URL: `http://localhost:8000`

All requests and responses use JSON. Timestamps are ISO 8601 with UTC timezone.

---

## Endpoints

### POST /sessions

Create a new session with candidate metadata.

**Request Body:**
```json
{
  "candidate_name": "Rahul Sharma",
  "candidate_email": "rahul.sharma@example.com",
  "interviewer_names": ["Alice Chen"],
  "scheduled_start_time": "2024-01-15T10:00:00Z"
}
```

All fields are optional. If omitted, the system uses default/fallback values and agents that depend on these fields (e.g., NameMatcher) will produce neutral scores.

**Response (200):**
```json
{
  "session_id": "a36fffa7-dce6-46ba-8045-434c478cf97e",
  "status": "created"
}
```

**Errors:** None (always succeeds when well-formed).

---

### GET /sessions/{session_id}

Retrieve full session state.

**Response (200):**
```json
{
  "session_id": "a36fffa7-dce6-46ba-8045-434c478cf97e",
  "candidate_name": "Rahul Sharma",
  "candidate_email": "rahul.sharma@example.com",
  "interviewer_names": ["Alice Chen"],
  "scheduled_start_time": "2024-01-15T10:00:00Z",
  "created_at": "2024-01-15T09:58:00Z",
  "current_time": "2024-01-15T10:05:00Z",
  "participants": [
    {
      "participant_id": "p_001",
      "display_name": "Rahul Sharma",
      "join_timestamp": "2024-01-15T09:58:00Z",
      "leave_timestamp": null,
      "webcam_on": true,
      "webcam_frames": [],
      "speaking_activity": [],
      "speaking_duration_total": 0.0
    }
  ],
  "transcript": [],
  "prior_probabilities": {},
  "confidence_history": [],
  "event_log": []
}
```

**Errors:**
- `404` — Session not found

---

### GET /sessions/{session_id}/participants

List all participants with their basic info.

**Response (200):**
```json
[
  {
    "participant_id": "p_001",
    "display_name": "Rahul Sharma"
  },
  {
    "participant_id": "p_002",
    "display_name": "Alice Chen"
  }
]
```

Note: This endpoint returns basic participant info. For per-participant evidence and probabilities, use the `/candidate` endpoint which includes `candidate_probabilities` and `participant_evidence` fields.

**Errors:**
- `404` — Session not found

---

### GET /sessions/{session_id}/candidate

Run the full evaluation pipeline and return the current top candidate with evidence.

**Response (200):**
```json
{
  "participant_id": "p_001",
  "display_name": "Rahul Sharma",
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
  "candidate_probabilities": {
    "p_001": 0.87,
    "p_002": 0.13
  },
  "participant_evidence": {
    "p_001": [
      { "agent": "NameMatcher", "score": 0.3, "weight": 0.15, "reasoning": "..." },
      { "agent": "TemporalAgent", "score": 0.85, "weight": 0.20, "reasoning": "..." }
    ],
    "p_002": [
      { "agent": "NameMatcher", "score": 0.0, "weight": 0.15, "reasoning": "..." },
      { "agent": "TemporalAgent", "score": 0.5, "weight": 0.20, "reasoning": "..." }
    ]
  },
  "arbitrator_explanation": "Combined evidence from 6 active agents with global weight redistribution applied.",
  "updated_at": "2024-01-15T10:23:45Z"
}
```

**Fields:**
| Field | Description |
|-------|-------------|
| `participant_id` | ID of the top candidate |
| `display_name` | Current display name of the top candidate |
| `candidate_probability` | Posterior probability (0–1) of the top candidate |
| `is_candidate` | True when confidence_tier is HIGH or MEDIUM |
| `confidence_tier` | HIGH (≥0.85), MEDIUM (0.65–0.84), LOW (0.45–0.64), UNCERTAIN (<0.45) |
| `evidence` | Evidence array for the top candidate only |
| `candidate_probabilities` | All participants' probabilities |
| `participant_evidence` | Per-participant evidence arrays |
| `arbitrator_explanation` | Natural language summary of the decision |
| `updated_at` | Timestamp of this evaluation |

**Errors:**
- `404` — Session not found
- `400` — No participants in session

**Notes:**
- Calling this endpoint triggers a full re-evaluation and appends to the confidence history
- Agents that are globally inactive (None for all participants) appear with weight=0 and descriptive reasoning
- Scores are clamped to `[1e-6, 1-1e-6]` for numerical stability

---

### GET /sessions/{session_id}/confidence-history

Retrieve the time-series of probability changes for all participants.

**Response (200):**
```json
{
  "session_id": "a36fffa7-dce6-46ba-8045-434c478cf97e",
  "history": [
    {
      "timestamp": "2024-01-15T09:58:00Z",
      "probabilities": {
        "p_001": 0.63,
        "p_002": 0.37
      }
    },
    {
      "timestamp": "2024-01-15T10:00:00Z",
      "probabilities": {
        "p_001": 0.71,
        "p_002": 0.29
      }
    },
    {
      "timestamp": "2024-01-15T10:02:00Z",
      "probabilities": {
        "p_001": 0.87,
        "p_002": 0.13
      }
    }
  ]
}
```

Note: History entries are appended on every event injection and every `/candidate` GET request. The history can be used to render confidence evolution charts on the dashboard.

**Errors:**
- `404` — Session not found

---

### POST /sessions/{session_id}/events

Inject a session event. Triggers immediate re-evaluation of all participants.

**Supported Event Types:**

#### participant_join
```json
{
  "type": "participant_join",
  "timestamp": "2024-01-15T09:58:00Z",
  "participant_id": "p_001",
  "display_name": "Rahul Sharma",
  "webcam_on": true
}
```

#### participant_leave
```json
{
  "type": "participant_leave",
  "timestamp": "2024-01-15T10:30:00Z",
  "participant_id": "p_001"
}
```

#### name_change
```json
{
  "type": "name_change",
  "timestamp": "2024-01-15T10:05:00Z",
  "participant_id": "p_001",
  "new_name": "Rahul Sharma"
}
```

#### transcript
```json
{
  "type": "transcript",
  "timestamp": "2024-01-15T10:01:00Z",
  "participant_id": "p_001",
  "utterance": "I can walk you through my recent project.",
  "duration_seconds": 35.0
}
```

#### speaking_activity
```json
{
  "type": "speaking_activity",
  "timestamp": "2024-01-15T10:01:35Z",
  "participant_id": "p_001",
  "activity": [true, true, false, false, true, false, false, false, false, false]
}
```
Each boolean represents one second of speaking activity. Extends the participant's `speaking_activity` array.

#### webcam_frame
```json
{
  "type": "webcam_frame",
  "timestamp": "2024-01-15T10:00:02Z",
  "participant_id": "p_001",
  "face_count": 1,
  "webcam_on": true
}
```

**Response (200):**
```json
{
  "status": "processed",
  "event_type": "participant_join"
}
```

Response includes updated probabilities and evidence, available via `GET /candidate`.

**Errors:**
- `404` — Session not found
- `400` — Missing required fields for the event type, or unsupported event type
- `422` — Malformed JSON or invalid field types

---

### WebSocket /sessions/{session_id}/ws

Stream real-time candidate updates. Messages are JSON with the following structure:

**candidate_update** (sent immediately after every event injection):
```json
{
  "type": "candidate_update",
  "session_id": "a36fffa7-dce6-46ba-8045-434c478cf97e",
  "data": {
    "participant_id": "p_001",
    "candidate_probability": 0.87,
    "confidence_tier": "HIGH",
    "is_candidate": true,
    "candidate_probabilities": { "p_001": 0.87, "p_002": 0.13 },
    "evidence": {
      "p_001": [ { "agent": "NameMatcher", "score": 0.3, "weight": 0.15, "reasoning": "..." } ],
      "p_002": [ { "agent": "NameMatcher", "score": 0.0, "weight": 0.15, "reasoning": "..." } ]
    },
    "arbitrator_explanation": "Combined evidence from 6 active agents with global weight redistribution applied.",
    "updated_at": "2024-01-15T10:23:45Z"
  }
}
```

**heartbeat_update** (sent every 30 seconds by background task, same data shape):
```json
{
  "type": "heartbeat_update",
  "session_id": "a36fffa7-dce6-46ba-8045-434c478cf97e",
  "data": { "... same fields as candidate_update ..." }
}
```

**Errors:**
- `4004` — Session not found (close code)

---

### GET /health

Service health check.

**Response (200):**
```json
{
  "status": "ok"
}
```

**Errors:** None.

---

## Data Models

### SessionState
| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | UUID v4 |
| `candidate_name` | string | null Full name from calendar invite |
| `candidate_email` | string | null Email from calendar invite |
| `interviewer_names` | string[] | Expected interviewer names |
| `scheduled_start_time` | ISO 8601 | null Scheduled interview start |
| `created_at` | ISO 8601 | null Session creation timestamp |
| `current_time` | ISO 8601 | null Most recent event timestamp |
| `participants` | Participant[] | Array of participant objects |
| `transcript` | TranscriptUtterance[] | Array of utterances |
| `prior_probabilities` | Record<string, float> | Current probabilities per participant |
| `confidence_history` | ConfidenceHistoryEntry[] | Time series of probability snapshots |
| `event_log` | SessionEventEntry[] | Chronological event log |

### Participant
| Field | Type | Description |
|-------|------|-------------|
| `participant_id` | string | Unique identifier |
| `display_name` | string | Name shown in meeting UI |
| `join_timestamp` | ISO 8601 | null When participant joined |
| `leave_timestamp` | ISO 8601 | null When participant left |
| `webcam_on` | boolean | Whether webcam is active |
| `webcam_frames` | WebcamFrame[] | Sampled frame metadata |
| `speaking_activity` | boolean[] | Second-by-second speaking detection |
| `speaking_duration_total` | float | Cumulative speaking seconds |

### TranscriptUtterance
| Field | Type | Description |
|-------|------|-------------|
| `speaker_id` | string | Maps to participant_id |
| `utterance` | string | Spoken text |
| `timestamp` | ISO 8601 | When utterance occurred |
| `duration_seconds` | float | null Utterance duration |

### EvidenceItem
| Field | Type | Description |
|-------|------|-------------|
| `agent` | string | Agent name (e.g. "NameMatcher") |
| `score` | float | null Agent score in [0, 1] or null if inactive |
| `weight` | float | Effective weight after redistribution |
| `reasoning` | string | Natural language explanation |

### ConfidenceTier
`HIGH` | `MEDIUM` | `LOW` | `UNCERTAIN`

---

## Agent Score Reference

| Agent | Score Range | Weight | Meaning |
|-------|-------------|--------|---------|
| NameMatcher | [0, 1] | 0.15 | 1.0 = exact name match; 0.1 = generic name; 0.0 = interviewer match |
| TemporalAgent | [0, 0.9] | 0.20 | Peaks at 0.9 for exactly on-time join; decays via Gaussian |
| BehavioralAgent | [0, 1] | 0.25 | >0.6 = burst pattern; <0.4 = uniform interviewer pattern |
| SoloWindowAgent | [0, 1] or None | 0.25 | None when no solo window exists; 1.0 for >3min solo |
| FaceConsistencyAgent | [0, 1] or None | 0.10 | None when webcam off; penalized for multi-face/absence |
| LLMReasoningAgent | [0, 1] | 0.05 | 0.5 when rate-limited or API unavailable |
