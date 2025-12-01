import Search from "./Search";

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-900 text-slate-100 flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-5xl space-y-6">
        {/* App header */}
        <header className="text-center space-y-1">
          <h1 className="text-4xl font-bold tracking-tight">
            EchoHelp
          </h1>
          <p className="text-sm text-slate-300">
            AI-powered resolution memory for busy IT teams
          </p>
        </header>

        {/* Main console card */}
        <main className="rounded-2xl border border-slate-800 bg-slate-900/70 shadow-2xl backdrop-blur-md p-4 sm:p-6 lg:p-8">
          <Search />
        </main>
        {/* Floating Ask Echo widget removed: inline AskEchoWidget is used inside Search.tsx */}
      </div>
    </div>
  );
}
