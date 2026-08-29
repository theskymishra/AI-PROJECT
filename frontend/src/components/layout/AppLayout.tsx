/**
 * Application shell: sidebar, header, scrolling content region.
 *
 * SimulationProvider wraps everything, so the whole tree reads simulation
 * state from one SSE connection. Backend health is resolved once here for
 * build information; the live connection signal comes from the stream, not
 * from polling.
 */

import { Outlet } from "react-router";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useBackendHealth } from "@/hooks/useBackendHealth";
import { SimulationProvider, useSimulation } from "@/store/SimulationProvider";

function Shell() {
  // Health polling stands down while the stream is open: an open SSE
  // connection already proves the backend is alive, so polling it as well
  // would be redundant traffic.
  const { streamStatus } = useSimulation();
  const backend = useBackendHealth({ paused: streamStatus === "open" });

  return (
    <div className="flex h-screen overflow-hidden bg-bg text-fg">
      <Sidebar backend={backend} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header backend={backend} />
        <main className="flex-1 overflow-y-auto p-5">
          <Outlet context={backend} />
        </main>
      </div>
    </div>
  );
}

export function AppLayout() {
  return (
    <SimulationProvider>
      <Shell />
    </SimulationProvider>
  );
}
