import type { EvidenceItem } from "../types";

type Props = {
  evidence: EvidenceItem[];
};

function scoreTone(score: number | null): "strong" | "moderate" | "weak" | "inactive" {
  if (score === null) {
    return "inactive";
  }
  if (score >= 0.8) {
    return "strong";
  }
  if (score >= 0.5) {
    return "moderate";
  }
  return "weak";
}

export function EvidencePanel({ evidence }: Props) {
  const sortedEvidence = [...evidence].sort((left, right) => right.weight - left.weight);

  return (
    <section className="status-card">
      <div className="status-header">
        <div>
          <p className="eyebrow">Evidence</p>
          <h2>Agent Breakdown</h2>
        </div>
        <span className="participant-count">{sortedEvidence.length}</span>
      </div>

      {sortedEvidence.length ? (
        <div className="evidence-list">
          {sortedEvidence.map((item) => {
            const tone = scoreTone(item.score);
            return (
              <article key={item.agent} className={`evidence-card evidence-card--${tone}`}>
                <div className="evidence-card__header">
                  <div>
                    <h3>{item.agent}</h3>
                    <p>Weight {Math.round(item.weight * 100)}%</p>
                  </div>
                  <strong>{item.score === null ? "Inactive" : `${Math.round(item.score * 100)}%`}</strong>
                </div>
                <p>{item.reasoning}</p>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="muted-copy">Agent evidence will appear once the orchestrator evaluates at least one participant.</p>
      )}
    </section>
  );
}
