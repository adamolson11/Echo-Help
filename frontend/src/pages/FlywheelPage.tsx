import FlywheelWidget from "../FlywheelWidget";
import SectionHeader from "../ui/SectionHeader";

export default function FlywheelPage() {
  return (
    <div>
      <SectionHeader
        title="Flywheel"
        description="Run one issue through recommendation, execution, outcome capture, and stored learning."
      />
      <FlywheelWidget />
    </div>
  );
}
