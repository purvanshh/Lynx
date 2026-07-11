# Lynx Candidate Identification System

Lynx is a real-time, multi-agent system for identifying the likely interview candidate in a live meeting. The product combines multiple weak signals, fuses them with a log-odds Bayesian arbitrator, and returns both a confidence score and an explanation trail.

This repo now contains the initial product docs plus a full boilerplate scaffold for the backend, simulator, dashboard, tests, and scripts. Most modules are intentionally placeholder-first so the architecture is in place before deeper implementation work.

## Current Status

- Updated PRD with the corrected log-odds arbitrator specification
- Full repo structure scaffolded
- Minimal FastAPI, simulator, dashboard, and test boilerplate in place
- Agent implementations are stubs and should be refined iteratively

## Core Documents

- PRD: [docs/PRD.md](/Users/purvansh/Desktop/Projects/Lynx/docs/PRD.md)
- Architecture notes: [docs/ARCHITECTURE.md](/Users/purvansh/Desktop/Projects/Lynx/docs/ARCHITECTURE.md)
- API notes: [docs/API.md](/Users/purvansh/Desktop/Projects/Lynx/docs/API.md)

## Repository Structure

```text
lynx/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── docs/
├── lynx/
├── simulator/
├── dashboard/
├── tests/
├── scripts/
└── .github/
```

## Quick Start

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn lynx.api.main:app --reload
```

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

## Notes

- The arbitrator scaffold follows the updated PRD's log-odds linear pooling approach.
- The current dashboard is a static shell wired for future API integration.
- Scenario JSON files and test fixtures are placeholders to make the structure concrete.
