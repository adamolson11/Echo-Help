
import React from "react";
import Search from "./Search";
import InsightsPanel from "./InsightsPanel";

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-start justify-center">
      <div className="w-full max-w-5xl px-4 py-8">
        <Search />
        <InsightsPanel />
      </div>
    </div>
  );
}
