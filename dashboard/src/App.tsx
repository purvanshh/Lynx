import { ConfidenceMeter } from "./components/ConfidenceMeter";
import { EvidencePanel } from "./components/EvidencePanel";
import { ParticipantCard } from "./components/ParticipantCard";
import { SessionTimeline } from "./components/SessionTimeline";
import { UncertaintyBanner } from "./components/UncertaintyBanner";

export default function App() {
  return (
    <main style={{ fontFamily: "Georgia, serif", padding: 32, maxWidth: 1080, margin: "0 auto" }}>
      <h1>Lynx Dashboard</h1>
      <p>Initial dashboard shell for live candidate-confidence monitoring.</p>
      <UncertaintyBanner />
      <ConfidenceMeter probability={0.5} />
      <ParticipantCard name="Rahul Sharma" probability={0.5} />
      <EvidencePanel />
      <SessionTimeline />
    </main>
  );
}
