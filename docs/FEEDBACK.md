# Human Feedback Loop

Lynx supports a human-in-the-loop feedback mechanism that adapts agent weights based on operator corrections. This transforms the system from static weights to continuously improving fusion.

## How It Works

1. An operator observes a session and decides whether the system's top candidate is correct
2. They click **Mark Correct** or **Mark Incorrect** on the dashboard
3. `POST /sessions/{id}/feedback` is called with the correct candidate ID
4. The weight adapter performs an EMA (Exponential Moving Average) update:

   ```
   correction = weight + (agent_score - 0.5) * 0.2
   new_weight = weight + 0.15 * (correction - weight)
   ```

   - Agents that scored the correct candidate highly → weight increases
   - Agents that scored the correct candidate lowly → weight decreases
   - Inactive agents (no score) → weight decays slightly

5. Weights are clamped to [0.02, 0.50] and re-normalized to sum to 1.0
6. Adapted weights persist to `data/adapted_weights.json`

## API

```http
POST /sessions/{id}/feedback
Content-Type: application/json

{
  "correct_candidate_id": "participant_abc",
  "confidence": 0.95,
  "notes": "Clear candidate from the transcript"
}
```

Response:
```json
{
  "status": "feedback_applied",
  "session_id": "...",
  "correct_candidate_id": "participant_abc",
  "adapted_weights": {
    "NameMatcher": 0.16,
    "TemporalAgent": 0.17,
    ...
  }
}
```

## Weight Adaptation Trace

Each feedback call produces an audit trail. The adapted weights file accumulates
all changes and serves as the new default on restart:

```json
{
  "NameMatcher": 0.1623,
  "TemporalAgent": 0.1731,
  "BehavioralAgent": 0.2310,
  ...
}
```

## Bounds

| Constraint | Value |
|-----------|-------|
| Minimum weight | 0.02 |
| Maximum weight | 0.50 |
| EMA alpha | 0.15 |
