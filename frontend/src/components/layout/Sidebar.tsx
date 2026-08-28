/**
 * Left navigation rail.
 *
 * Renders from APP_ROUTES, so it grows by one entry per phase rather than
 * showing eight destinations that do not exist yet.
 */

import { NavLink } from "react-router";

import { StatusBadge } from "@/components/layout/StatusBadge";
import { APP_ROUTES } from "@/components/layout/routes";
import type { BackendHealth } from "@/hooks/useBackendHealth";

interface SidebarProps {
  backend: BackendHealth;
}

export function Sidebar({ backend }: SidebarProps) {
  const phase = backend.health?.phase ?? null;
  const totalPhases = backend.health?.total_phases ?? null;

  return (
    <nav
      aria-label="Primary"
      className="flex w-56 shrink-0 flex-col border-r border-border bg-panel"
    >
      <div className="border-b border-border px-4 py-3.5">
        <div className="font-mono text-[15px] font-semibold tracking-[0.18em] text-fg">
          AI&#8209;DERS
        </div>
        <div className="mt-0.5 text-2xs leading-tight text-fg-muted">
          Emergency Operations Center
        </div>
      </div>

      <ul className="flex flex-1 flex-col gap-0.5 p-2">
        {APP_ROUTES.map((route) => {
          const Icon = route.icon;
          return (
            <li key={route.path}>
              <NavLink
                to={route.path}
                end={route.path === "/"}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-2.5 rounded-panel px-2.5 py-2 text-[13px] transition-colors duration-150",
                    isActive
                      ? "bg-panel-2 text-fg"
                      : "text-fg-muted hover:bg-panel-2 hover:text-fg",
                  ].join(" ")
                }
              >
                <Icon aria-hidden="true" className="size-4 shrink-0" />
                <span>{route.label}</span>
              </NavLink>
            </li>
          );
        })}
      </ul>

      <div className="border-t border-border px-4 py-3">
        <div className="text-2xs tracking-wide text-fg-muted uppercase">
          System Status
        </div>
        <div className="mt-1.5">
          {backend.state === "online" ? (
            <StatusBadge tone="safe">Online</StatusBadge>
          ) : backend.state === "checking" ? (
            <StatusBadge tone="info" pulse>
              Checking
            </StatusBadge>
          ) : (
            <StatusBadge tone="crit">Offline</StatusBadge>
          )}
        </div>
        {phase !== null && totalPhases !== null && (
          <div className="mt-2 font-mono text-2xs text-fg-muted">
            BUILD PHASE {phase}/{totalPhases}
          </div>
        )}
      </div>
    </nav>
  );
}
