import { startTransition, useEffect, useState } from "react";

import { api } from "../api/client";
import type { AnomalyInfo, CandidateOutput, ConfidenceHistoryPoint, Session } from "../types";

export function useSession(sessionId: string) {
  const [session, setSession] = useState<Session | null>(null);
  const [candidate, setCandidate] = useState<CandidateOutput | null>(null);
  const [history, setHistory] = useState<ConfidenceHistoryPoint[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      setCandidate(null);
      setHistory([]);
      setAnomalies([]);
      setError(null);
      return;
    }

    let active = true;

    async function loadSnapshot() {
      setLoading(true);
      try {
        const [sessionResponse, candidateResponse, historyResponse, anomaliesResponse] = await Promise.all([
          api.getSession(sessionId),
          api.getCandidate(sessionId),
          api.getConfidenceHistory(sessionId),
          api.getAnomalies(sessionId),
        ]);

        if (!active) {
          return;
        }

        startTransition(() => {
          setSession(sessionResponse);
          setCandidate(candidateResponse);
          setHistory(historyResponse.history);
          setAnomalies(anomaliesResponse.anomalies ?? []);
          setError(null);
        });
      } catch (loadError) {
        if (!active) {
          return;
        }
        const message = loadError instanceof Error ? loadError.message : "Unknown session loading error";
        startTransition(() => {
          setError(message);
        });
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void loadSnapshot();
    const interval = window.setInterval(() => {
      void loadSnapshot();
    }, 5000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [sessionId]);

  return { session, candidate, history, anomalies, loading, error };
}
