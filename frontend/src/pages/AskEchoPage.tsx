import AskEchoWidget from "../AskEchoWidget";
import SectionHeader from "../ui/SectionHeader";

export default function AskEchoPage() {
  return (
    <div>
      <SectionHeader
        title="Answer Trail"
        description="Inspect the underlying Ask Echo answer, sources, and feedback trail."
      />
      <AskEchoWidget />
    </div>
  );
}
