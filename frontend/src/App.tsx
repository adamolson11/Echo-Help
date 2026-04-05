import { useEffect, useState } from "react";
import "./App.css";
import ConsoleShell from "./ConsoleShell";
import { ROUTE_LABELS, navigateToConsole, parseAppRoute, type AppRoute, type ConsoleRoute } from "./appRoutes";
import AskEchoPage from "./pages/AskEchoPage";
import FlywheelPage from "./pages/FlywheelPage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import InsightsPage from "./pages/InsightsPage";
import IntakePage from "./pages/IntakePage";
import TicketDetailPage from "./pages/TicketDetailPage";

export default function App() {
  const [appRoute, setAppRoute] = useState<AppRoute>(() => parseAppRoute());

  useEffect(() => {
    function syncRoute() {
      setAppRoute(parseAppRoute());
    }

    window.addEventListener("hashchange", syncRoute);
    return () => window.removeEventListener("hashchange", syncRoute);
  }, []);

  function renderRoute(r: ConsoleRoute) {
    if (r === "ask") return <AskEchoPage />;
    if (r === "search") return <FlywheelPage />;
    if (r === "kb") return <KnowledgeBasePage />;
    if (r === "insights") return <InsightsPage />;
    if (r === "intake") return <IntakePage />;
    return <FlywheelPage />;
  }

  const activeConsoleRoute = appRoute.kind === "console" ? appRoute.route : null;
  const routeLabel = appRoute.kind === "ticket" ? `tickets/${appRoute.ticketId}` : ROUTE_LABELS[appRoute.route];

  return (
    <ConsoleShell
      route={activeConsoleRoute}
      routeLabel={routeLabel}
      onRouteChange={(route) => {
        setAppRoute({ kind: "console", route });
        navigateToConsole(route);
      }}
      title="E.C.O."
      subtitle="Executive Command Operations"
    >
      {appRoute.kind === "ticket" ? <TicketDetailPage ticketId={appRoute.ticketId} /> : renderRoute(appRoute.route)}
    </ConsoleShell>
  );
}
