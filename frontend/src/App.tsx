import { useState } from "react";
import ConsoleShell, { getInitialConsoleRoute, type ConsoleRoute } from "./ConsoleShell";
import AskEchoPage from "./pages/AskEchoPage";
import SearchPage from "./pages/SearchPage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import InsightsPage from "./pages/InsightsPage";
import IntakePage from "./pages/IntakePage";

export default function App() {
  const [route, setRoute] = useState<ConsoleRoute>(() => getInitialConsoleRoute());

  function renderRoute(r: ConsoleRoute) {
    if (r === "ask") return <AskEchoPage />;
    if (r === "search") return <SearchPage />;
    if (r === "kb") return <KnowledgeBasePage />;
    if (r === "insights") return <InsightsPage />;
    if (r === "intake") return <IntakePage />;
    return <AskEchoPage />;
  }

  return (
    <ConsoleShell
      route={route}
      onRouteChange={setRoute}
      title="EchoHelp"
      subtitle="AI-powered resolution memory for busy IT teams"
    >
      {renderRoute(route)}
    </ConsoleShell>
  );
}
