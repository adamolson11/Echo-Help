
import Search from "./Search";
import AskEchoWidget from "./AskEchoWidget";

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-slate-100 flex items-start justify-center">
      <div className="w-full max-w-6xl px-4 py-8">
        <div className="mx-auto">
          <AskEchoWidget />
          <Search />
        </div>
      </div>
    </div>
  );
}
