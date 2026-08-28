/**
 * Application shell: sidebar, header, scrolling content region.
 *
 * Backend health is resolved once here and passed down, rather than being
 * fetched independently by each consumer. Phase 2 replaces this with a single
 * SimulationProvider holding one SSE connection, following the same principle:
 * one source, many readers.
 */

import { Outlet } from "react-router";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { useBackendHealth } from "@/hooks/useBackendHealth";

export function AppLayout() {
  const backend = useBackendHealth();

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
