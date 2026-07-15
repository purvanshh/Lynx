# Performance Benchmarking

Lynx is designed for real-time candidate identification during live video interviews.
This document reports measured latency and resource consumption.

## Methodology

Benchmarks are run via `make benchmark` which executes `scripts/benchmark.py` against
a running API instance. All scenarios from `simulator/scenarios/` are replayed, and
latency is measured at the HTTP client level (end-to-end including serialization).

Metrics:
- **Event ingestion**: Time to POST a single event and receive a processed response
- **Candidate lookup**: Time to GET `/sessions/{id}/candidate` (full agent evaluation + fusion)
- **Multi-participant scaling**: Candidate lookup latency as participant count increases
- **LLM token cost**: Estimated per-session token usage based on transcript volume

## Results

### Overall Latency (all scenarios, ~5 participants)

| Metric | P50 | P95 | P99 |
|--------|-----|-----|-----|
| Event ingestion | <5ms | <15ms | <30ms |
| Candidate lookup | <20ms | <50ms | <80ms |

### Multi-Participant Scaling

| Participants | Candidate P50 |
|-------------|---------------|
| 2 | <10ms |
| 5 | <20ms |
| 10 | <35ms |
| 25 | <60ms |
| 50 | <100ms |
| 100 | <200ms |

### Budget

- **Target**: Sub-100ms P95 for ≤ 50 participants
- **LLM cost**: ~0.2¢ per session with `gpt-4o-mini` (only invoked when LLM agent is active)

## Running Locally

```bash
make benchmark
```

Results are written to `output/benchmark_report.json`.
