import Intake from "../Intake";
import SectionHeader from "../ui/SectionHeader";

export default function IntakePage() {
  return (
    <div>
      <SectionHeader
        title="Intake Assist"
        description="Triage new requests by matching similar past tickets."
      />
      <Intake />
    </div>
  );
}
