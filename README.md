# Sherlock Candidate Identification System

Sherlock is a real-time, multi-agent candidate identification system for interview calls. It is designed to identify the most likely candidate among meeting participants using evidence fusion across multiple signals, while keeping the reasoning explainable and uncertainty visible.

This repository is intentionally starting with documentation only. The Bayesian fusion math and implementation details will be refined later.

## Current Status

- Documentation-first scaffold
- PRD captured in Markdown
- No code or implementation added yet

## Proposed Repository Structure

```text
lynx/
├── README.md
└── docs/
    └── PRD.md
```

## Planned Structure

The fuller target structure from the current PRD is expected to evolve into:

```text
sherlock-candidate-id/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   └── API.md
├── sherlock/
├── simulator/
├── dashboard/
├── tests/
├── scripts/
└── .github/
```

## PRD

The working product requirements document is available at [docs/PRD.md](/Users/purvansh/Desktop/Projects/Lynx/docs/PRD.md).
