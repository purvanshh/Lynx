# Lynx Candidate Identification System

Lynx is a real-time candidate identification platform for live interview sessions. It combines multiple weak signals, fuses them through a Bayesian log-odds arbitrator, and returns a ranked candidate prediction with evidence, confidence, and a human-readable explanation trail.

The repository is being built in implementation phases. The current codebase already supports core evidence fusion, event-driven session updates, and scenario playback scaffolding, while the roadmap extends toward a full demo-ready product with richer simulation, dashboard visualization, and production-grade integrations.

## Vision

Lynx is designed to answer a specific operational question during a live interview:

`Which participant is most likely the interview candidate right now, and why?`

To answer that reliably, the system combines:

- Identity heuristics from names and email handles
- Join-time behavior around the scheduled start
- Speaking-pattern analysis from transcript activity
- Solo-window detection before interviewers join
- Webcam consistency checks across sampled frames
- LLM-based synthesis for edge cases and explanation

## Current Capabilities

The implementation in this repository currently provides:

- A FastAPI backend for session retrieval and live candidate evaluation
- A central agent orchestrator that evaluates all enabled agents per participant
- Bayesian evidence fusion with global weight redistribution for inactive agents
- Candidate scoring with:
  - `NameMatcherAgent`
  - `TemporalAgent`
  - `BehavioralAgent`
  - `SoloWindowAgent`
  - `FaceConsistencyAgent`
  - `LLMReasoningAgent`
- Session creation and event injection endpoints
- Confidence-history tracking over time
- A simulator scheduler that can load scenario JSON, emit ordered events, and drive the API
- Unit and integration tests covering the orchestration and API pipeline

## Roadmap Capabilities

The planned full system extends beyond the current implementation and is intended to support:

- Richer interview scenarios across ambiguous and adversarial meeting setups
- Dashboard views for evidence panels, confidence trends, and timeline playback
- More realistic simulator data, including transcript streams, webcam sampling, and speaking activity
- Stronger LLM integration for structured justification and sanity-check reasoning
- Expanded API coverage for demo operations, debugging, and observability
- Production-oriented persistence, deployment, and monitoring workflows

In short, the repo is moving from a strong backend prototype toward a complete PRD-aligned live demo system.

## Architecture Overview

At a high level, Lynx works as follows:

1. A session is created with candidate metadata and interview schedule context.
2. Live or simulated events update participants, transcript data, webcam observations, and speaking activity.
3. The orchestrator asks each agent to score every participant.
4. The arbitrator fuses those signals into posterior candidate probabilities.
5. The API returns the current top candidate, evidence items, confidence tier, and explanation.
6. Confidence history is stored so the system can show how certainty evolves during the interview.

## Repository Structure

```text
lynx/
├── lynx/                     # Backend application code
│   ├── agents/               # Signal-producing agents
│   ├── api/                  # FastAPI routes and schemas
│   ├── arbitrator/           # Bayesian fusion logic
│   ├── models/               # Pydantic domain models
│   ├── store/                # Session storage layer
│   └── utils/                # Shared helpers
├── simulator/                # Scenario playback and event scheduling
├── dashboard/                # Frontend shell for future visualization work
├── tests/                    # Unit and integration test coverage
├── docs/                     # PRD, architecture, and API notes
├── scripts/                  # Local development entry points
├── requirements.txt          # Runtime and test dependencies
└── pyproject.toml            # Project metadata and pytest config
```

## API Surface

The backend currently exposes these primary endpoints:

- `GET /health`
- `POST /sessions`
- `GET /sessions/{session_id}`
- `GET /sessions/{session_id}/participants`
- `POST /sessions/{session_id}/events`
- `GET /sessions/{session_id}/candidate`
- `GET /sessions/{session_id}/confidence-history`

These endpoints are sufficient to create a session, stream updates into it, evaluate the current candidate, and inspect confidence evolution.

## Quick Start

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn lynx.api.main:app --reload
```

### Simulator

```bash
python scripts/run_simulator.py
```

For richer scenario playback, the scheduler is built to support JSON scenarios with timed event emission and API injection.

### Dashboard

```bash
cd dashboard
npm install
npm run dev
```

### Tests

```bash
pytest
```

## Core Documents

- PRD: [docs/PRD.md](/Users/purvansh/Desktop/Projects/Lynx/docs/PRD.md)
- Architecture notes: [docs/ARCHITECTURE.md](/Users/purvansh/Desktop/Projects/Lynx/docs/ARCHITECTURE.md)
- API notes: [docs/API.md](/Users/purvansh/Desktop/Projects/Lynx/docs/API.md)

## Development Notes

- The backend uses log-odds linear pooling rather than naive multiplicative blending.
- Agents may return `None` when a signal is globally inactive, and the arbitrator redistributes weights accordingly.
- The simulator and dashboard are intentionally evolving alongside the backend rather than after it.
- Some future-facing hooks already exist in the models and scheduler so later phases can land without major rewrites.

## Status

The project is no longer just a scaffold. It now has a functioning candidate-evaluation pipeline, event ingestion flow, and simulator backbone. The remaining phases are focused on broadening realism, product polish, and PRD completeness rather than inventing the system from scratch.
