import type {
  AnomalyInfo,
  CandidateOutput,
  ConfidenceHistoryPoint,
  CreateSessionRequest,
  EventRequest,
  Participant,
  Session,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with status ${response.status}`);
  }

  return (await response.json()) as T;
}

export const api = {
  createSession: (data: CreateSessionRequest) =>
    request<{ session_id: string; status: string }>("/sessions", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getSession: (sessionId: string) => request<Session>(`/sessions/${sessionId}`),
  getParticipants: (sessionId: string) =>
    request<Array<Pick<Participant, "participant_id" | "display_name">>>(`/sessions/${sessionId}/participants`),
  getCandidate: (sessionId: string) => request<CandidateOutput>(`/sessions/${sessionId}/candidate`),
  getConfidenceHistory: (sessionId: string) =>
    request<{ session_id: string; history: ConfidenceHistoryPoint[] }>(`/sessions/${sessionId}/confidence-history`),
  injectEvent: (sessionId: string, event: EventRequest) =>
    request<{ status: string; event_type: string }>(`/sessions/${sessionId}/events`, {
      method: "POST",
      body: JSON.stringify(event),
    }),
  getAnomalies: (sessionId: string) =>
    request<{ session_id: string; anomalies: AnomalyInfo[] }>(`/sessions/${sessionId}/anomalies`),
  submitFeedback: (sessionId: string, correctCandidateId: string, confidence?: number, notes?: string) =>
    request<{ status: string; session_id: string; correct_candidate_id: string; adapted_weights: Record<string, number> }>(
      `/sessions/${sessionId}/feedback`,
      {
        method: "POST",
        body: JSON.stringify({ correct_candidate_id: correctCandidateId, confidence, notes }),
      },
    ),
  getAnalyticsSummary: () =>
    request<AnalyticsSummary>("/analytics/summary"),
};
