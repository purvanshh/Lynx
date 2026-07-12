import { startTransition, useEffect, useState } from "react";

import { api } from "../api/client";
import type { CandidateOutput, ConfidenceHistoryPoint, Session } from "../types";

export function useSession(sessionId: string) {
  const [session, setSession] = useState<Session | null>(null);
  const [candidate, setCandidate] = useState<CandidateOutput | null>(null);
  const [history, setHistory] = useState<ConfidenceHistoryPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      setCandidate(null);
      setHistory([]);
      setError(null);
      return;
    }

    let active = true;

    async function loadSnapshot() {
      setLoading(true);
      try {
        const [sessionResponse, candidateResponse, historyResponse] = await Promise.all([
          api.getSession(sessionId),
          api.getCandidate(sessionId),
          api.getConfidenceHistory(sessionId),
        ]);

        if (!active) {
          return;
        }

        startTransition(() => {
          setSession(sessionResponse);
          setCandidate(candidateResponse);
          setHistory(historyResponse.history);
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

  return { session, candidate, history, loading, error };
}
