type TopCandidate = {
  participantId: string;
  displayName: string;
  probability: number;
};

type AnomalyInfo = {
  rule: string;
  severity: string;
  message: string;
};

type Props = {
  tier?: "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN";
  topTwo?: TopCandidate[];
  anomalies?: AnomalyInfo[];
};

const SEVERITY_COLORS: Record<string, string> = {
  warning: "#f59e0b",
  info: "#3b82f6",
};

export function UncertaintyBanner({ tier = "UNCERTAIN", topTwo = [], anomalies = [] }: Props) {
  const showUncertainty = tier === "UNCERTAIN";

  return (
    <>
      {showUncertainty && (
        <section className="uncertainty-banner">
          <div>
            <p className="eyebrow">Operator Attention</p>
            <h2>High Uncertainty Detected</h2>
            <p>Signal disagreement is preventing a confident candidate identification. Human review is recommended.</p>
          </div>
          <ul>
            {topTwo.length ? (
              topTwo.map((candidate) => (
                <li key={candidate.participantId}>
                  <strong>{candidate.displayName}</strong>
                  <span>{Math.round(candidate.probability * 100)}%</span>
                </li>
              ))
            ) : (
              <li>
                <strong>Awaiting candidates</strong>
                <span>No scored participants yet</span>
              </li>
            )}
          </ul>
        </section>
      )}
      {anomalies.length > 0 && (
        <section className="anomaly-banner">
          <div className="anomaly-header">
            <p className="eyebrow">Anomaly Alert</p>
            <h2>{anomalies.length} Anomal{anomalies.length === 1 ? "y" : "ies"} Detected</h2>
          </div>
          <ul className="anomaly-list">
            {anomalies.map((anomaly, idx) => (
              <li key={idx} style={{ borderLeftColor: SEVERITY_COLORS[anomaly.severity] ?? "#6b7280" }}>
                <strong>{anomaly.rule.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</strong>
                <span>{anomaly.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
