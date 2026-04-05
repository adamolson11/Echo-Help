import Intake from "../Intake";
import TicketCreateForm from "../components/TicketCreateForm";
import SectionHeader from "../ui/SectionHeader";

export default function IntakePage() {
  return (
    <div className="space-y-4">
      <SectionHeader
        title="Intake Assist"
        description="Triage new requests by matching similar past tickets."
      />
      <TicketCreateForm />
      <Intake />
    </div>
  );
}
