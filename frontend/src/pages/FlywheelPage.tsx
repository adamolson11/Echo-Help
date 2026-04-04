import FlywheelWidget from "../FlywheelWidget";
import SectionHeader from "../ui/SectionHeader";

export default function FlywheelPage() {
  return (
    <div>
      <SectionHeader
        title="Ask Echo"
        description="Search one issue, choose one next action, run the steps, and save the learning."
      />
      <FlywheelWidget />
    </div>
  );
}
