import AskEchoWidget from "../AskEchoWidget";
import SectionHeader from "../ui/SectionHeader";

export default function AskEchoPage() {
  return (
    <div className="ask-echo-page">
      <SectionHeader
        title="Ask Echo"
        description="Ask a support question, inspect the answer trail, and capture feedback without leaving the console."
      />
      <AskEchoWidget />
    </div>
  );
}
