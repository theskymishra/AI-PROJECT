/**
 * Route table.
 *
 * Routes are registered as they are implemented. The catch-all sends unknown
 * paths back to the dashboard rather than to a dead end.
 */

import { Navigate, Route, Routes } from "react-router";

import { AppLayout } from "@/components/layout/AppLayout";
import { Dashboard } from "@/pages/Dashboard";
import { DisasterMapPage } from "@/pages/DisasterMapPage";
import { RiskPage } from "@/pages/RiskPage";
import { ReasoningPage } from "@/pages/ReasoningPage";
import { ResourcesPage } from "@/pages/ResourcesPage";
import { PlanningPage } from "@/pages/PlanningPage";
import { EvidencePage } from "@/pages/EvidencePage";
import { ExecutionPage } from "@/pages/ExecutionPage";
import { MonitoringPage } from "@/pages/MonitoringPage";
import { ExplainabilityPage } from "@/pages/ExplainabilityPage";
import { RoutingPage } from "@/pages/RoutingPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="map" element={<DisasterMapPage />} />
        <Route path="routing" element={<RoutingPage />} />
        <Route path="risk" element={<RiskPage />} />
        <Route path="reasoning" element={<ReasoningPage />} />
        <Route path="resources" element={<ResourcesPage />} />
        <Route path="planning" element={<PlanningPage />} />
        <Route path="evidence" element={<EvidencePage />} />
        <Route path="execution" element={<ExecutionPage />} />
        <Route path="monitoring" element={<MonitoringPage />} />
        <Route path="explainability" element={<ExplainabilityPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
