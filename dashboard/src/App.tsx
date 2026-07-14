import { FormEvent, useEffect, useMemo, useState } from "react";

import { ConfidenceMeter } from "./components/ConfidenceMeter";
import { EvidencePanel } from "./components/EvidencePanel";
import { ParticipantCard } from "./components/ParticipantCard";
import { SessionTimeline } from "./components/SessionTimeline";
import { UncertaintyBanner } from "./components/UncertaintyBanner";
import { useSession } from "./hooks/useSession";
import type { Participant } from "./types";

function formatScheduledTime(value: string | null): string {
  if (!value) {
    return "Not scheduled";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function App() {
  const initialSessionId =
    new URLSearchParams(window.location.search).get("sessionId") ?? window.localStorage.getItem("lynx-session-id") ?? "";
  const [draftSessionId, setDraftSessionId] = useState(initialSessionId);
  const [activeSessionId, setActiveSessionId] = useState(initialSessionId);
  const [selectedParticipantId, setSelectedParticipantId] = useState<string | null>(null);
  const { session, candidate, history, anomalies, loading, error } = useSession(activeSessionId);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (activeSessionId) {
      url.searchParams.set("sessionId", activeSessionId);
      window.localStorage.setItem("lynx-session-id", activeSessionId);
    } else {
      url.searchParams.delete("sessionId");
      window.localStorage.removeItem("lynx-session-id");
    }
    window.history.replaceState({}, "", url);
  }, [activeSessionId]);

  useEffect(() => {
    if (!session?.participants.length) {
      setSelectedParticipantId(null);
      return;
    }

    const participantIds = new Set(session.participants.map((participant) => participant.participant_id));
    if (selectedParticipantId && participantIds.has(selectedParticipantId)) {
      return;
    }

    setSelectedParticipantId(candidate?.participant_id ?? session.participants[0]?.participant_id ?? null);
  }, [candidate?.participant_id, selectedParticipantId, session?.participants]);

  const participantLookup = useMemo(() => {
    return new Map(session?.participants.map((participant) => [participant.participant_id, participant]) ?? []);
  }, [session?.participants]);

  const sortedParticipants = useMemo(() => {
    if (!session?.participants) {
      return [];
    }
    const probabilities = candidate?.candidate_probabilities ?? {};
    return [...session.participants].sort((left, right) => {
      const probabilityDelta = (probabilities[right.participant_id] ?? 0) - (probabilities[left.participant_id] ?? 0);
      if (probabilityDelta !== 0) {
        return probabilityDelta;
      }
      return left.display_name.localeCompare(right.display_name);
    });
  }, [candidate?.candidate_probabilities, session?.participants]);

  const selectedParticipant: Participant | null =
    (selectedParticipantId ? participantLookup.get(selectedParticipantId) : null) ?? null;

  const topTwo = useMemo(() => {
    if (!candidate?.candidate_probabilities) {
      return [];
    }
    return Object.entries(candidate.candidate_probabilities)
      .sort((left, right) => right[1] - left[1])
      .slice(0, 2)
      .map(([participantId, probability]) => ({
        participantId,
        displayName: participantLookup.get(participantId)?.display_name ?? participantId,
        probability,
      }));
  }, [candidate?.candidate_probabilities, participantLookup]);

  function handleSessionSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setActiveSessionId(draftSessionId.trim());
  }

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Live Candidate Identification</p>
          <h1>Lynx Operations Dashboard</h1>
          <p className="hero-copy">
            Track the active session, inspect the fusion evidence behind each decision, and intervene quickly when the
            system surfaces uncertainty.
          </p>
        </div>
        <form className="session-form" onSubmit={handleSessionSubmit}>
          <label htmlFor="session-id">Session ID</label>
          <div className="session-form-row">
            <input
              id="session-id"
              name="session-id"
              value={draftSessionId}
              onChange={(event) => setDraftSessionId(event.target.value)}
              placeholder="Enter an active session ID"
            />
            <button type="submit">Load Session</button>
          </div>
          <p className="session-form-hint">The dashboard polls the API every 5 seconds and remembers the last session.</p>
        </form>
      </section>

      <UncertaintyBanner tier={candidate?.confidence_tier} topTwo={topTwo} anomalies={anomalies} />

      {!activeSessionId ? (
        <section className="empty-state">
          <h2>Choose a Session</h2>
          <p>Enter a live session ID to populate the dashboard with participants, evidence, and confidence history.</p>
        </section>
      ) : null}

      {error ? (
        <section className="status-card error-card">
          <h2>Session Load Error</h2>
          <p>{error}</p>
        </section>
      ) : null}

      {activeSessionId ? (
        <section className="content-grid">
          <div className="primary-column">
            <section className="status-card">
              <div className="status-header">
                <div>
                  <p className="eyebrow">Current Decision</p>
                  <h2>{candidate?.display_name ?? "Awaiting participant data"}</h2>
                </div>
                <div className={`live-pill ${loading ? "live-pill--loading" : ""}`}>{loading ? "Refreshing" : "Live"}</div>
              </div>
              <div className="status-metadata">
                <div>
                  <span>Session</span>
                  <strong>{session?.session_id ?? activeSessionId}</strong>
                </div>
                <div>
                  <span>Candidate of Record</span>
                  <strong>{session?.candidate_name ?? "Unknown"}</strong>
                </div>
                <div>
                  <span>Scheduled Start</span>
                  <strong>{formatScheduledTime(session?.scheduled_start_time ?? null)}</strong>
                </div>
              </div>
              <ConfidenceMeter
                probability={candidate?.candidate_probability ?? 0}
                tier={candidate?.confidence_tier ?? "UNCERTAIN"}
              />
              <p className="arbitrator-copy">
                {candidate?.arbitrator_explanation ?? "Confidence updates will appear after participants join the session."}
              </p>
            </section>

            <EvidencePanel evidence={candidate?.evidence ?? []} />

            <SessionTimeline
              events={session?.event_log ?? []}
              scheduledStartTime={session?.scheduled_start_time ?? null}
              selectedParticipantId={selectedParticipantId}
              onSelectParticipant={setSelectedParticipantId}
              participantLookup={participantLookup}
            />
          </div>

          <div className="secondary-column">
            <section className="status-card">
              <div className="status-header">
                <div>
                  <p className="eyebrow">Participants</p>
                  <h2>Room Snapshot</h2>
                </div>
                <span className="participant-count">{sortedParticipants.length}</span>
              </div>
              <div className="participant-stack">
                {sortedParticipants.map((participant) => (
                  <ParticipantCard
                    key={participant.participant_id}
                    participant={participant}
                    probability={candidate?.candidate_probabilities?.[participant.participant_id] ?? 0}
                    evidence={candidate?.participant_evidence?.[participant.participant_id] ?? []}
                    isTopCandidate={candidate?.participant_id === participant.participant_id}
                    isSelected={selectedParticipantId === participant.participant_id}
                    onSelect={setSelectedParticipantId}
                  />
                ))}
              </div>
            </section>

            <section className="status-card">
              <div className="status-header">
                <div>
                  <p className="eyebrow">History</p>
                  <h2>Confidence Checkpoints</h2>
                </div>
                <span className="participant-count">{history.length}</span>
              </div>
              {history.length ? (
                <ol className="history-list">
                  {history.slice(-6).reverse().map((entry) => {
                    const selectedProbability = selectedParticipantId
                      ? entry.probabilities[selectedParticipantId]
                      : candidate?.participant_id
                        ? entry.probabilities[candidate.participant_id]
                        : undefined;
                    return (
                      <li key={entry.timestamp}>
                        <strong>{new Date(entry.timestamp).toLocaleTimeString()}</strong>
                        <span>
                          {selectedParticipant?.display_name ?? candidate?.display_name ?? "Top candidate"}:{" "}
                          {selectedProbability !== undefined ? `${Math.round(selectedProbability * 100)}%` : "No signal"}
                        </span>
                      </li>
                    );
                  })}
                </ol>
              ) : (
                <p className="muted-copy">Confidence history will populate after the first event-driven evaluation.</p>
              )}
            </section>
          </div>
        </section>
      ) : null}
    </main>
  );
}
