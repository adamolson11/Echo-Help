import AskEchoWidget from "../AskEchoWidget";
import SectionHeader from "../ui/SectionHeader";

export default function AskEchoPage() {
  return (
    <div className="ask-echo-page">
      <SectionHeader
        title="Ask Echo"
        description="EchoHelp remembers what worked before. Ask a question, inspect past tickets, and Echo gets better from feedback."
      />
      <div className="ask-echo-page__frame">
        <AskEchoWidget />
      </div>
    </div>
  );
}
