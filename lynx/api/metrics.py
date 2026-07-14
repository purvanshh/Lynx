from prometheus_client import Counter, Gauge, Histogram

evaluation_latency = Histogram(
    "lynx_evaluation_latency_seconds",
    "Time to run a full agent evaluation cycle",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

agent_eval_time = Histogram(
    "lynx_agent_evaluation_latency_seconds",
    "Time per agent evaluation",
    labelnames=["agent"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0),
)

confidence_tier_gauge = Gauge(
    "lynx_confidence_tier",
    "Current confidence tier per session (1=HIGH, 2=MEDIUM, 3=LOW, 4=UNCERTAIN)",
    labelnames=["session_id"],
)

top_probability_gauge = Gauge(
    "lynx_top_candidate_probability",
    "Current top candidate probability per session",
    labelnames=["session_id"],
)

anomaly_counter = Counter(
    "lynx_anomalies_total",
    "Total anomaly alerts fired",
    labelnames=["rule"],
)

event_ingestion_latency = Histogram(
    "lynx_event_ingestion_latency_seconds",
    "Time to ingest a single event",
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)

active_sessions = Gauge(
    "lynx_active_sessions",
    "Number of active sessions currently tracked",
)

total_sessions_created = Counter(
    "lynx_sessions_created_total",
    "Total sessions created",
)

http_request_duration = Histogram(
    "lynx_http_request_duration_seconds",
    "HTTP request latency by endpoint",
    labelnames=["method", "path"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
