import type { SessionEvent } from "../types";

type Props = {
  events: SessionEvent[];
  scheduledStartTime: string | null;
  selectedParticipantId: string | null;
  onSelectParticipant: (participantId: string | null) => void;
  participantLookup: Map<string, { display_name: string }>;
};

const eventLabels: Record<SessionEvent["type"], string> = {
  participant_join: "Join",
  participant_leave: "Leave",
  name_change: "Name Change",
  transcript: "Transcript",
  speaking_activity: "Speaking Activity",
  webcam_frame: "Webcam Frame",
};

function formatOffset(timestamp: string, scheduledStartTime: string | null): string {
  if (!scheduledStartTime) {
    return new Date(timestamp).toLocaleTimeString();
  }

  const deltaSeconds =
    Math.round((new Date(timestamp).getTime() - new Date(scheduledStartTime).getTime()) / 1000);
  const sign = deltaSeconds >= 0 ? "+" : "-";
  const absoluteSeconds = Math.abs(deltaSeconds);
  const minutes = Math.floor(absoluteSeconds / 60);
  const seconds = absoluteSeconds % 60;
  return `${sign}${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

export function SessionTimeline({
  events,
  scheduledStartTime,
  selectedParticipantId,
  onSelectParticipant,
  participantLookup,
}: Props) {
  return (
    <section className="status-card">
      <div className="status-header">
        <div>
          <p className="eyebrow">Timeline</p>
          <h2>Session Event Stream</h2>
        </div>
        <span className="participant-count">{events.length}</span>
      </div>

      {events.length ? (
        <ol className="timeline-list">
          {events.map((event, index) => {
            const participantId = event.participant_id;
            const isSelected = participantId !== null && participantId === selectedParticipantId;
            const label =
              participantId !== null
                ? participantLookup.get(participantId)?.display_name ?? event.display_name ?? participantId
                : event.display_name ?? "Session";

            return (
              <li key={`${event.timestamp}-${event.type}-${index}`} className={isSelected ? "timeline-item timeline-item--selected" : "timeline-item"}>
                <button type="button" onClick={() => onSelectParticipant(participantId)} className="timeline-item__button">
                  <span className={`timeline-dot timeline-dot--${event.type}`} aria-hidden="true" />
                  <div className="timeline-item__content">
                    <div className="timeline-item__topline">
                      <strong>{eventLabels[event.type]}</strong>
                      <span>{formatOffset(event.timestamp, scheduledStartTime)}</span>
                    </div>
                    <p>{label}</p>
                    {event.details ? <small>{event.details}</small> : null}
                  </div>
                </button>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="muted-copy">Incoming joins, renames, transcript segments, and webcam samples will appear here.</p>
      )}
    </section>
  );
}
