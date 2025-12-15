import AskEchoWidget from "../AskEchoWidget";
import SectionHeader from "../ui/SectionHeader";

export default function AskEchoPage() {
  return (
    <div>
      <SectionHeader
        title="Ask Echo"
        description="Ask questions grounded in your ticket history and KB."
      />
      <AskEchoWidget />
    </div>
  );
}
