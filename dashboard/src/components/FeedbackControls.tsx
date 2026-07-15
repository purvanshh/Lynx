import { useState } from "react";

import { api } from "../api/client";

type Props = {
  sessionId: string;
  topCandidateId: string | null;
  onFeedbackSubmitted: () => void;
};

export function FeedbackControls({ sessionId, topCandidateId, onFeedbackSubmitted }: Props) {
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function handleFeedback(correct: boolean) {
    if (!topCandidateId) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const res = await api.submitFeedback(sessionId, correct ? topCandidateId : "__none__");
      const adaptedCount = Object.keys(res.adapted_weights).length;
      setMessage(`Feedback applied. ${adaptedCount} agent weights adapted.`);
      onFeedbackSubmitted();
    } catch {
      setMessage("Failed to submit feedback.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="status-card">
      <div className="status-header">
        <div>
          <p className="eyebrow">Human Feedback</p>
          <h2>Mark Identification</h2>
        </div>
      </div>
      <p className="muted-copy" style={{ marginBottom: 12 }}>
        Confirm or correct the system's candidate identification to adapt agent weights.
      </p>
      <div className="feedback-row">
        <button
          className="feedback-btn feedback-btn--correct"
          disabled={submitting || !topCandidateId}
          onClick={() => handleFeedback(true)}
        >
          Mark Correct
        </button>
        <button
          className="feedback-btn feedback-btn--incorrect"
          disabled={submitting || !topCandidateId}
          onClick={() => handleFeedback(false)}
        >
          Mark Incorrect
        </button>
      </div>
      {message ? <p className="feedback-message">{message}</p> : null}
    </section>
  );
}