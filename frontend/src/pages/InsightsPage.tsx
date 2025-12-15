import InsightsPanel from "../InsightsPanel";
import SectionHeader from "../ui/SectionHeader";

export default function InsightsPage() {
  return (
    <div>
      <SectionHeader
        title="Insights"
        description="Feedback patterns, clusters, radars, and Ask Echo telemetry."
      />
      <InsightsPanel />
    </div>
  );
}
