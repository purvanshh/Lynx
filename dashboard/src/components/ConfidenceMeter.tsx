type Props = {
  probability: number;
  tier: "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN";
};

const tierCopy: Record<Props["tier"], string> = {
  HIGH: "Strong multi-signal alignment",
  MEDIUM: "Likely candidate, continue monitoring",
  LOW: "Weak signal strength",
  UNCERTAIN: "Ambiguous outcome, review required",
};

export function ConfidenceMeter({ probability, tier }: Props) {
  const percentage = Math.round(probability * 100);

  return (
    <section className="confidence-meter">
      <div className="confidence-meter__header">
        <div>
          <p className="eyebrow">Candidate Confidence</p>
          <h3>{percentage}%</h3>
        </div>
        <span className={`tier-pill tier-pill--${tier.toLowerCase()}`}>{tier}</span>
      </div>
      <div className="confidence-meter__track" aria-hidden="true">
        <div className={`confidence-meter__fill confidence-meter__fill--${tier.toLowerCase()}`} style={{ width: `${percentage}%` }} />
      </div>
      <p className="confidence-meter__copy">{tierCopy[tier]}</p>
    </section>
  );
}
