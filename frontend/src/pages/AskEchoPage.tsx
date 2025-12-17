import AskEchoWidget from "../AskEchoWidget";
import SectionHeader from "../ui/SectionHeader";

export default function AskEchoPage() {
  return (
    <div>
      <SectionHeader
        title="Ask Echo"
        description="EchoHelp remembers what worked before. Ask a question, inspect past tickets, and Echo gets better from feedback."
      />
      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-4">
        <AskEchoWidget />
      </div>
    </div>
  );
}
