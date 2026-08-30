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
import { RoutingPage } from "@/pages/RoutingPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="map" element={<DisasterMapPage />} />
        <Route path="routing" element={<RoutingPage />} />
        <Route path="risk" element={<RiskPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
