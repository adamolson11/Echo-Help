import InsightsPanel from "../InsightsPanel";
import SectionHeader from "../ui/SectionHeader";

export default function InsightsPage() {
  return (
    <div>
      <SectionHeader
        title="Insights"
        description="Signal summaries, outcome signals, and Ask Echo telemetry."
      />
      <InsightsPanel />
    </div>
  );
}
