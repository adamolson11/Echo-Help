import AskEchoWidget from "../AskEchoWidget";
import SectionHeader from "../ui/SectionHeader";

export default function AskEchoPage() {
  return (
    <div>
      <SectionHeader
        title="Ask Echo"
        description="Describe the issue, choose one next action, follow the steps, then save what happened so Echo can help faster next time."
      />
      <AskEchoWidget />
    </div>
  );
}
