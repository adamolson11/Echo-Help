export type ConsoleRoute = "flywheel" | "ask" | "search" | "kb" | "insights" | "intake";

export type AppRoute =
  | { kind: "console"; route: ConsoleRoute }
  | { kind: "ticket"; ticketId: number };

export const ROUTE_LABELS: Record<ConsoleRoute, string> = {
  flywheel: "Flywheel",
  ask: "Ask Echo",
  search: "Search",
  kb: "Knowledge Base",
  insights: "Insights",
  intake: "Intake Assist",
};

export function normalizeConsoleRoute(value: string | null): ConsoleRoute {
  const normalized = (value ?? "").trim().toLowerCase();
  if (
    normalized === "flywheel" ||
    normalized === "ask" ||
    normalized === "search" ||
    normalized === "kb" ||
    normalized === "insights" ||
    normalized === "intake"
  ) {
    return normalized;
  }
  return "flywheel";
}

export function parseAppRoute(): AppRoute {
  const rawHash = window.location.hash ?? "";
  const cleanedHash = rawHash.replace(/^#\/?/, "");
  const segments = cleanedHash.split("/").filter(Boolean);

  if (segments[0] === "tickets") {
    const ticketId = Number(segments[1]);
    if (Number.isFinite(ticketId)) {
      return { kind: "ticket", ticketId };
    }
  }

  return {
    kind: "console",
    route: normalizeConsoleRoute(segments[0] ?? "ask"),
  };
}

export function navigateToConsole(route: ConsoleRoute) {
  window.location.hash = `#/${route}`;
}

export function navigateToTicket(ticketId: number) {
  window.location.hash = `#/tickets/${ticketId}`;
}
