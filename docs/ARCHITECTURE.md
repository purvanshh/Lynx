# Architecture Notes

This document will hold implementation-level architecture decisions as the scaffold turns into a working system.

## Initial Boundaries

- `lynx/agents`: signal-specific inference
- `lynx/arbitrator`: log-odds fusion and confidence logic
- `lynx/store`: in-memory and persisted session state
- `lynx/api`: FastAPI surface
- `simulator/`: scenario playback and event generation
- `dashboard/`: operator-facing UI
