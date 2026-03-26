export type ConsoleRoute = "ask" | "search" | "kb" | "insights" | "intake";

export type AppRoute =
  | { kind: "console"; route: ConsoleRoute }
  | { kind: "ticket"; ticketId: number };

export const ROUTE_LABELS: Record<ConsoleRoute, string> = {
  ask: "Ask Echo",
  search: "Search",
  kb: "Knowledge Base",
  insights: "Insights",
  intake: "Intake Assist",
};

export function normalizeConsoleRoute(value: string | null): ConsoleRoute {
  const normalized = (value ?? "").trim().toLowerCase();
  if (
    normalized === "ask" ||
    normalized === "search" ||
    normalized === "kb" ||
    normalized === "insights" ||
    normalized === "intake"
  ) {
    return normalized;
  }
  return "ask";
}

function parseTicketPath(pathname: string): number | null {
  const match = pathname.match(/^\/tickets\/(\d+)\/?$/);
  if (!match) return null;

  const ticketId = Number(match[1]);
  return Number.isFinite(ticketId) ? ticketId : null;
}

function dispatchRouteChange() {
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function parseAppRoute(): AppRoute {
  const ticketId = parseTicketPath(window.location.pathname || "/");
  if (ticketId !== null) {
    return { kind: "ticket", ticketId };
  }

  const rawHash = window.location.hash ?? "";
  const cleanedHash = rawHash.replace(/^#\/?/, "");
  const firstSegment = cleanedHash.split("/")[0] ?? "";

  return {
    kind: "console",
    route: normalizeConsoleRoute(firstSegment),
  };
}

export function navigateToConsole(route: ConsoleRoute, options?: { replace?: boolean }) {
  const method = options?.replace ? "replaceState" : "pushState";
  window.history[method](null, "", `/#/${route}`);
  dispatchRouteChange();
}

export function navigateToTicket(ticketId: number, options?: { replace?: boolean }) {
  const method = options?.replace ? "replaceState" : "pushState";
  window.history[method](null, "", `/tickets/${ticketId}`);
  dispatchRouteChange();
}