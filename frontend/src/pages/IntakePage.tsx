import Intake from "../Intake";
import TicketCreateForm from "../components/TicketCreateForm";
import SectionHeader from "../ui/SectionHeader";

export default function IntakePage() {
  return (
    <div>
      <SectionHeader
        title="Intake Assist"
        description="Triage new requests by matching similar past tickets."
      />
      <div className="space-y-4">
      <TicketCreateForm />
      <Intake />
    </div>
    </div>
  );
}
