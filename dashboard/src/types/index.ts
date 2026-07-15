export interface Participant {
  participant_id: string;
  display_name: string;
  join_timestamp: string | null;
  leave_timestamp: string | null;
  webcam_on: boolean;
  speaking_duration_total: number;
}

export interface EvidenceItem {
  agent: string;
  score: number | null;
  weight: number;
  reasoning: string;
}

export interface CandidateOutput {
  participant_id: string;
  display_name: string;
  candidate_probability: number;
  is_candidate: boolean;
  confidence_tier: "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN";
  evidence: EvidenceItem[];
  candidate_probabilities: Record<string, number>;
  participant_evidence: Record<string, EvidenceItem[]>;
  arbitrator_explanation: string;
  updated_at: string;
}

export interface ConfidenceHistoryPoint {
  timestamp: string;
  probabilities: Record<string, number>;
}

export interface SessionEvent {
  timestamp: string;
  type: "participant_join" | "participant_leave" | "name_change" | "transcript" | "speaking_activity" | "webcam_frame";
  participant_id: string | null;
  display_name: string | null;
  details: string | null;
}

export interface Session {
  session_id: string;
  candidate_name: string | null;
  candidate_email: string | null;
  interviewer_names: string[];
  scheduled_start_time: string | null;
  created_at: string | null;
  current_time: string | null;
  participants: Participant[];
  confidence_history: ConfidenceHistoryPoint[];
  event_log: SessionEvent[];
}

export interface CreateSessionRequest {
  candidate_name?: string | null;
  candidate_email?: string | null;
  interviewer_names?: string[];
  scheduled_start_time?: string | null;
}

export interface AnomalyInfo {
  rule: string;
  severity: string;
  message: string;
  details: Record<string, unknown>;
}

export interface EventRequest {
  type: SessionEvent["type"];
  timestamp: string;
  participant_id?: string;
  display_name?: string;
  webcam_on?: boolean;
  new_name?: string;
  utterance?: string;
  duration_seconds?: number;
  activity?: boolean[];
  face_count?: number;
  image_path?: string;
}

export interface AnalyticsSummary {
  total_sessions: number;
  total_participants: number;
  total_events: number;
  tier_distribution: Record<string, number>;
  agent_activation_count: Record<string, number>;
  confidence_histogram: Array<{ bucket_lower: number; bucket_upper: number; count: number }>;
  average_confidence: number;
}
