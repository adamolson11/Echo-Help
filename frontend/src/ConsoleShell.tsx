import { useEffect } from "react";

export type ConsoleRoute = "ask" | "search" | "kb" | "insights" | "intake";

const ROUTE_LABELS: Record<ConsoleRoute, string> = {
  ask: "Ask Echo",
  search: "Search",
  kb: "Knowledge Base",
  insights: "Insights",
  intake: "Intake Assist",
};

function normalizeRoute(value: string | null): ConsoleRoute {
  const v = (value ?? "").trim().toLowerCase();
  if (v === "ask" || v === "search" || v === "kb" || v === "insights" || v === "intake") {
    return v;
  }
  return "ask";
}

function readRouteFromHash(): ConsoleRoute {
  // Support either '#/ask' or '#ask'
  const raw = window.location.hash ?? "";
  const cleaned = raw.replace(/^#\/?/, "");
  const firstSegment = cleaned.split("/")[0] ?? "";
  return normalizeRoute(firstSegment);
}

function setHashRoute(route: ConsoleRoute) {
  window.location.hash = `#/${route}`;
}

export default function ConsoleShell(props: {
  route: ConsoleRoute;
  onRouteChange: (r: ConsoleRoute) => void;
  title?: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const { route, onRouteChange, title, subtitle, children } = props;

  // Keep URL hash in sync for refresh/share.
  useEffect(() => {
    const expected = readRouteFromHash();
    if (expected !== route) setHashRoute(route);
  }, [route]);

  // If user changes hash manually, update route.
  useEffect(() => {
    function onHashChange() {
      const next = readRouteFromHash();
      onRouteChange(next);
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [onRouteChange]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 text-slate-100">
      <div className="mx-auto w-full max-w-7xl px-4 py-6">
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            <div className="text-2xl font-bold tracking-tight">{title ?? "EchoHelp"}</div>
            <div className="text-sm text-slate-300">{subtitle ?? "Resolution memory console"}</div>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400">
            <span className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1">Ctrl/⌘ K: Search</span>
            <span className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1">↑/↓: Navigate</span>
            <span className="rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1">Enter: Open</span>
          </div>
        </header>

        <div className="grid gap-4 md:grid-cols-[240px,1fr]">
          <nav className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3 backdrop-blur">
            <div className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Tools</div>

            {(Object.keys(ROUTE_LABELS) as ConsoleRoute[]).map((key) => {
              const isActive = key === route;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => onRouteChange(key)}
                  className={
                    "mb-1 w-full rounded-xl px-3 py-2 text-left text-sm transition " +
                    (isActive
                      ? "bg-indigo-500/20 text-slate-50 border border-indigo-500/40"
                      : "border border-transparent hover:border-slate-700 hover:bg-slate-800/60 text-slate-200")
                  }
                >
                  <div className="font-medium">{ROUTE_LABELS[key]}</div>
                </button>
              );
            })}

            <div className="mt-3 border-t border-slate-800 pt-3 px-2 text-xs text-slate-400">
              Route: <span className="text-slate-200">{route}</span>
            </div>
          </nav>

          <main className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-6 backdrop-blur">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}

export function getInitialConsoleRoute(): ConsoleRoute {
  // On first load, honor hash.
  return readRouteFromHash();
}
