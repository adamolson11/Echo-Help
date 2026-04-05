import FlywheelWidget from "../FlywheelWidget";
import SectionHeader from "../ui/SectionHeader";

export default function FlywheelPage() {
  return (
    <div>
      <SectionHeader
        title="Flywheel"
        description="Canonical E.C.O. loop: describe the problem, choose one action, run the steps, record the outcome, and save what should be reused next time."
      />
      <FlywheelWidget />
    </div>
  );
}