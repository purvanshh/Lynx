import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from "recharts";

import { api } from "../api/client";
import type { AnalyticsSummary } from "../types";

const TIER_COLORS: Record<string, string> = {
  HIGH: "#1f9964",
  MEDIUM: "#d6a022",
  LOW: "#df7d34",
  UNCERTAIN: "#cf4d4d",
};

const CHART_COLORS = ["#3280d7", "#41cf8f", "#ffb562", "#965fda", "#cf4d4d", "#27b070", "#d6a022"];

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const result = await api.getAnalyticsSummary();
        if (active) setData(result);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : "Failed to load analytics");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    const interval = window.setInterval(load, 10000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  if (loading) {
    return (
      <main className="app-shell">
        <section className="hero-panel"><p>Loading analytics...</p></section>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="app-shell">
        <section className="status-card error-card"><h2>Error</h2><p>{error}</p></section>
      </main>
    );
  }

  const tierData = Object.entries(data.tier_distribution).map(([name, value]) => ({ name, value }));
  const agentData = Object.entries(data.agent_activation_count).map(([name, value]) => ({ name, value }));
  const histData = data.confidence_histogram.map((b) => ({
    range: `${(b.bucket_lower * 100).toFixed(0)}-${(b.bucket_upper * 100).toFixed(0)}%`,
    count: b.count,
  }));

  return (
    <main className="app-shell">
      <section className="hero-panel">
        <div>
          <p className="eyebrow">Cross-Session View</p>
          <h1>Operations Analytics</h1>
          <p className="hero-copy">Aggregated metrics across all sessions. Auto-refreshes every 10 seconds.</p>
        </div>
      </section>

      <div className="analytics-grid">
        <section className="status-card">
          <p className="eyebrow">Sessions</p>
          <h2 className="analytics-big-number">{data.total_sessions}</h2>
        </section>
        <section className="status-card">
          <p className="eyebrow">Participants</p>
          <h2 className="analytics-big-number">{data.total_participants}</h2>
        </section>
        <section className="status-card">
          <p className="eyebrow">Events Processed</p>
          <h2 className="analytics-big-number">{data.total_events}</h2>
        </section>
        <section className="status-card">
          <p className="eyebrow">Avg Confidence</p>
          <h2 className="analytics-big-number">{(data.average_confidence * 100).toFixed(1)}%</h2>
        </section>
      </div>

      <div className="analytics-charts">
        <section className="status-card">
          <div className="status-header"><div><p className="eyebrow">Distribution</p><h2>Confidence Tier Breakdown</h2></div></div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={tierData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {tierData.map((entry) => (
                  <Cell key={entry.name} fill={TIER_COLORS[entry.name] ?? "#888"} />
                ))}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </section>

        <section className="status-card">
          <div className="status-header"><div><p className="eyebrow">Distribution</p><h2>Confidence Histogram</h2></div></div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={histData}>
              <XAxis dataKey="range" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#3280d7" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </section>

        <section className="status-card">
          <div className="status-header"><div><p className="eyebrow">Activity</p><h2>Agent Activation Heatmap</h2></div></div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={agentData} layout="vertical">
              <XAxis type="number" />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={120} />
              <Tooltip />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {agentData.map((_, idx) => (
                  <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>
    </main>
  );
}