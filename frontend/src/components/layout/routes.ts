/**
 * Route registry.
 *
 * The sidebar renders FROM this list. Only routes that are actually
 * implemented appear here, so navigation can never lead to an empty page.
 *
 * The project brief specifies nine sidebar entries. Eight of them have no
 * functionality until later phases, and rendering them disabled would be a
 * placeholder wearing a badge -- which the brief also forbids. Registering
 * routes as they are built resolves the conflict and makes progress visible.
 *
 * Each phase appends its own entry:
 *   Phase 6  AI Reasoning
 *   Phase 7  Resources
 *   Phase 8  Planning
 *   Phase 10 Emergencies
 *   Phase 12 Analytics
 */

import { Activity, Brain, LayoutDashboard, Map, Route } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface AppRoute {
  path: string;
  label: string;
  icon: LucideIcon;
  /** Phase that introduced this route. Shown as a build marker in the sidebar. */
  phase: number;
}

export const APP_ROUTES: readonly AppRoute[] = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard, phase: 1 },
  { path: "/map", label: "Disaster Map", icon: Map, phase: 3 },
  { path: "/routing", label: "AI Routing", icon: Route, phase: 4 },
  { path: "/risk", label: "Risk Analysis", icon: Activity, phase: 5 },
  { path: "/reasoning", label: "AI Reasoning", icon: Brain, phase: 6 },
] as const;
