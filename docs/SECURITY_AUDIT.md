# Security Audit — Adversarial Attack Resistance

## Methodology

We generated **1,000 adversarial scenarios** across **8 attack classes** (125 variants each) and ran them through the full candidate identification pipeline. Each variant randomizes key parameters (join offset, utterance duration, face count, toggle count, generic name choice, etc.) to ensure statistical coverage.

### Attack success definition

An attack is considered successful only if the system **fails to correctly identify the ground-truth candidate at the final checkpoint** (300s), either by:
- Identifying the wrong participant (false positive)
- Remaining in the UNCERTAIN tier

Temporary false positives during intermediate checkpoints (30s, 60s, 120s) that resolve by 300s are **not** counted as attack successes, but are flagged for review.

### Target

Attack success rate **< 5%** across all 1,000 variants.

---

## Results

| Attack | Variants | Success Rate | False Positives | Final Accuracy |
|---|---|---|---|---|
| Impersonation | 125 | 0.00% | 125* | 100% |
| Silent Candidate | 125 | 0.00% | 0 | 100% |
| Face Swap | 125 | 0.00% | 0 | 100% |
| Collusion | 125 | 0.00% | 0 | 100% |
| Name Collision | 125 | 0.00% | 0 | 100% |
| Rapid Name Change | 125 | 0.00% | 0 | 100% |
| Webcam Toggle | 125 | 0.00% | 0 | 100% |
| Generic Names | 125 | 0.00% | 0 | 100% |
| **Total** | **1,000** | **0.00%** | **125** | **100%** |

\* Temporary false positives during intermediate checkpoints — see Impersonation note below.

---

## Attack Descriptions & Analysis

### 1. Impersonation
- **Vector**: The interviewer (p_002) joins early, speaks in long burst-style utterances (avg 25–50s), and behaves like a candidate. The real candidate (p_001) joins late and asks short questions.
- **Result**: System never loses final accuracy.
- **Note**: At early checkpoints (30s, 60s) before p_001 has joined, the system correctly identifies p_002 as the only participant with a candidate-like signal. Once p_001 joins and establishes their identity, the system converges to p_001 by 120s–300s. These are **not** security false positives — the system correctly identifies the most candidate-like participant given available data.

### 2. Silent Candidate
- **Vector**: The real candidate never speaks. The interviewer does all talking.
- **Result**: NameMatcher + TemporalAgent provide enough signal to identify the candidate even with zero transcript data.

### 3. Face Swap
- **Vector**: Candidate starts with `face_count=1`, then switches to `face_count=0` or `face_count=2` mid-session.
- **Result**: FaceConsistencyAgent penalizes the score, but other agents (NameMatcher, Temporal, Behavioral) compensate.

### 4. Collusion
- **Vector**: Two interviewers both speak in long burst patterns, mimicking candidate behavior.
- **Result**: SoloWindowAgent + NameMatcher + Temporal provide orthogonal signals that distinguish the candidate from multiple interviewers.

### 5. Name Collision
- **Vector**: Interviewer uses the session's `candidate_name` as display name. The real candidate uses a different name.
- **Result**: NameMatcher correctly gives score 0.0 to the interviewer (matches interviewer list) and the candidate's non-matching name still scores via `fuzz.ratio`.

### 6. Rapid Name Change
- **Vector**: Candidate changes display name 3–6 times during the session.
- **Result**: NameMatcher re-evaluates on each change; the candidate's name at join time plus consistent behavioral/temporal signals maintains identification.

### 7. Webcam Toggle
- **Vector**: Candidate toggles webcam on/off 3–8 times during the session.
- **Result**: Each toggle incurs a 10% penalty from FaceConsistencyAgent, but the penalty is bounded and other agents dominate.

### 8. Generic Names
- **Vector**: Both participants use generic device names (e.g., "iPhone", "MacBook Pro").
- **Result**: NameMatcher gives a floor score of 0.1 to both participants; TemporalAgent + BehavioralAgent differentiate.

---

## Key Findings

1. **No attack produced a final false positive** — the system correctly identified the ground-truth candidate in all 1,000 variants.
2. **Bayesian fusion is the key defense** — individual agents can be weakened by targeted attacks, but the ensemble corrects for any single agent's degradation.
3. **Impersonation causes temporary uncertainty** — when the real candidate hasn't joined yet, the system assigns high probability to the most candidate-like participant. This is correct behavior, not a vulnerability.
4. **Silent candidates are still identifiable** — Name matching and temporal proximity are sufficient signals even without transcript data.

---

## Recommendations

1. **Add a "participant_not_yet_present" indicator** — the impersonation false-positive flag could be eliminated by not evaluating candidate confidence until all expected participants have joined.
2. **Strengthen webcam toggle penalty** — current 10% per toggle is mild; consider compounding or a cap of 50% score reduction for >5 toggles.
3. **Add adversarial monitoring** — rapid name changes (>3 in a session) and webcam toggles (>5) should raise operational alerts, even if they don't affect final accuracy.

---

## Reproduction

```bash
make stress-test
```

Runs 1,000 adversarial variants through the in-process API. Report written to `output/stress_test_report.json`.
