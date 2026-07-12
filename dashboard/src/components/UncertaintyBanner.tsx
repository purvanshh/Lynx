type TopCandidate = {
  participantId: string;
  displayName: string;
  probability: number;
};

type Props = {
  tier?: "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN";
  topTwo?: TopCandidate[];
};

export function UncertaintyBanner({ tier = "UNCERTAIN", topTwo = [] }: Props) {
  if (tier !== "UNCERTAIN") {
    return null;
  }

  return (
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
  );
}
