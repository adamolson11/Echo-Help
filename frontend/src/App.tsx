
import Search from "./Search";
import AskEchoWidget from "./AskEchoWidget";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-start justify-center">
      <div className="w-full max-w-5xl px-4 py-8">
        <AskEchoWidget />
        <Search />
      </div>
    </div>
  );
}
