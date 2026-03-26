import { useEffect, useState } from "react";
import "./App.css";
import ConsoleShell from "./ConsoleShell";
import { navigateToConsole, parseAppRoute, type AppRoute, type ConsoleRoute } from "./appRoutes";
import AskEchoPage from "./pages/AskEchoPage";
import SearchPage from "./pages/SearchPage";
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
    window.addEventListener("popstate", syncRoute);
    return () => {
      window.removeEventListener("hashchange", syncRoute);
      window.removeEventListener("popstate", syncRoute);
    };
  }, []);

  function renderRoute(r: ConsoleRoute) {
    if (r === "ask") return <AskEchoPage />;
    if (r === "search") return <SearchPage />;
    if (r === "kb") return <KnowledgeBasePage />;
    if (r === "insights") return <InsightsPage />;
    if (r === "intake") return <IntakePage />;
    return <AskEchoPage />;
  }

  const activeConsoleRoute = appRoute.kind === "console" ? appRoute.route : null;
  const routeLabel =
    appRoute.kind === "ticket" ? `tickets/${appRoute.ticketId}` : appRoute.route;

  return (
    <ConsoleShell
      route={activeConsoleRoute}
      routeLabel={routeLabel}
      onRouteChange={(route) => {
        setAppRoute({ kind: "console", route });
        navigateToConsole(route);
      }}
      title="EchoHelp"
      subtitle="AI-powered resolution memory for busy IT teams"
    >
      {appRoute.kind === "ticket" ? <TicketDetailPage ticketId={appRoute.ticketId} /> : renderRoute(appRoute.route)}
    </ConsoleShell>
  );
}
