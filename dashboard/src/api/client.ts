import type { CandidateSummary } from "../types";

const API_BASE = "http://localhost:8000";

export async function fetchCandidate(sessionId: string): Promise<CandidateSummary> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/candidate`);
  if (!response.ok) {
    throw new Error("Failed to fetch candidate");
  }
  return response.json() as Promise<CandidateSummary>;
}
