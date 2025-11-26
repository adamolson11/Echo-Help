import React from "react";
import Search from "./Search";

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-900 text-slate-100 relative overflow-hidden">
      {/* Cinematic glow background */}
      <div className="pointer-events-none absolute inset-0 opacity-40">
        <div className="w-[140%] h-[140%] -left-20 -top-32 bg-[radial-gradient(circle_at_top,_#4f46e5_0,_transparent_55%),radial-gradient(circle_at_bottom,_#0ea5e9_0,_transparent_55%)] blur-3xl" />
      </div>

      {/* Centered content */}
      <div className="relative z-10 w-full px-4 flex items-center justify-center">
        <Search />
      </div>
    </div>
  );
}
