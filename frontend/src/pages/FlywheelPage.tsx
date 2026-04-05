import Search from "../Search";
import SectionHeader from "../ui/SectionHeader";

export default function FlywheelPage() {
  return (
    <div>
      <SectionHeader
        title="E.C.O. Flywheel"
        description="Input and search, choose an action, run steps, capture the outcome, and save reusable learning in one canonical loop."
      />
      <Search />
    </div>
  );
}
