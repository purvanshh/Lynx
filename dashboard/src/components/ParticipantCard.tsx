import type { EvidenceItem, Participant } from "../types";

type Props = {
  participant: Participant;
  probability: number;
  evidence: EvidenceItem[];
  isTopCandidate: boolean;
  isSelected: boolean;
  onSelect: (participantId: string) => void;
};

export function ParticipantCard({
  participant,
  probability,
  evidence,
  isTopCandidate,
  isSelected,
  onSelect,
}: Props) {
  return (
    <article
      className={`participant-card ${isTopCandidate ? "participant-card--leader" : ""} ${isSelected ? "participant-card--selected" : ""}`}
    >
      <button className="participant-card__summary" type="button" onClick={() => onSelect(participant.participant_id)}>
        <div>
          <div className="participant-card__title-row">
            <h3>{participant.display_name}</h3>
            {isTopCandidate ? <span className="participant-badge">Top Candidate</span> : null}
          </div>
          <p>{participant.participant_id}</p>
        </div>
        <div className="participant-card__meta">
          <strong>{Math.round(probability * 100)}%</strong>
          <span className={participant.webcam_on ? "webcam-pill webcam-pill--on" : "webcam-pill webcam-pill--off"}>
            {participant.webcam_on ? "Webcam On" : "Webcam Off"}
          </span>
        </div>
      </button>

      <details open={isSelected}>
        <summary>View evidence</summary>
        <div className="participant-card__details">
          {evidence.length ? (
            <ul className="participant-evidence-list">
              {evidence.map((item) => (
                <li key={`${participant.participant_id}-${item.agent}`}>
                  <strong>{item.agent}</strong>
                  <span>{item.score === null ? "Inactive" : `${Math.round(item.score * 100)}%`}</span>
                  <p>{item.reasoning}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted-copy">No participant-specific evidence has been published yet.</p>
          )}
        </div>
      </details>
    </article>
  );
}
