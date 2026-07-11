import { useEffect, useState } from "react";

import type { CandidateSummary } from "../types";
import { fetchCandidate } from "../api/client";

export function useSession(sessionId: string) {
  const [candidate, setCandidate] = useState<CandidateSummary | null>(null);

  useEffect(() => {
    fetchCandidate(sessionId).then(setCandidate).catch(() => setCandidate(null));
  }, [sessionId]);

  return { candidate };
}
