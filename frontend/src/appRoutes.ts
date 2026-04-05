export type ConsoleRoute = "ask" | "search" | "kb" | "insights" | "intake";

export type AppRoute =
  | { kind: "console"; route: ConsoleRoute }
  | { kind: "ticket"; ticketId: number };

export const ROUTE_LABELS: Record<ConsoleRoute, string> = {
  ask: "Ask Echo (Inspection)",
  search: "E.C.O. Flywheel",
  kb: "Knowledge Base",
  insights: "Insights",
  intake: "Intake Assist",
};

export function normalizeConsoleRoute(value: string | null): ConsoleRoute {
  const normalized = (value ?? "").trim().toLowerCase();
  if (
    normalized === "ask" ||
    normalized === "flywheel" ||
    normalized === "search" ||
    normalized === "kb" ||
    normalized === "insights" ||
    normalized === "intake"
  ) {
    return normalized === "flywheel" ? "search" : normalized;
  }
  return "search";
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
    route: normalizeConsoleRoute(segments[0] ?? "flywheel"),
  };
}

export function navigateToConsole(route: ConsoleRoute) {
  window.location.hash = `#/${route === "search" ? "flywheel" : route}`;
}

export function navigateToTicket(ticketId: number) {
  window.location.hash = `#/tickets/${ticketId}`;
}
