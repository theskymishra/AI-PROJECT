/**
 * Disaster map DOM tests.
 *
 * WHAT THESE PROVE
 *   every entity in the snapshot is rendered
 *   road status reaches the DOM, and CHANGES when the backend says so
 *   flood shading tracks zone flood_level
 *   hover and click behave
 *   the static dashboard embed really is inert
 *
 * WHAT THESE DO NOT PROVE
 *   anything visual. jsdom performs no layout and computes no styles, so a
 *   test here cannot tell you the map is readable, well spaced, or legible on
 *   a projector. That still needs a human with a browser, and no number of
 *   green ticks below changes it.
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { DisasterMap } from "@/components/map/DisasterMap";
import type {
  Ambulance,
  Emergency,
  Hospital,
  Road,
  Shelter,
  WorldNode,
  Zone,
} from "@/types";

afterEach(cleanup);

/* -- fixtures, shaped exactly like the backend snapshot -------------------- */

const nodes: WorldNode[] = [
  { id: "N1", name: "Riverside Quay", x: 100, y: 620, zone_id: "Z1", kind: "JUNCTION" },
  { id: "N5", name: "Riverside North", x: 250, y: 430, zone_id: "Z1", kind: "JUNCTION" },
  { id: "N10", name: "Midtown West", x: 390, y: 400, zone_id: "Z2", kind: "JUNCTION" },
  { id: "N12", name: "Central General", x: 470, y: 250, zone_id: "Z2", kind: "FACILITY" },
  { id: "N18", name: "Highland School", x: 900, y: 240, zone_id: "Z3", kind: "FACILITY" },
];

const zones: Zone[] = [
  {
    id: "Z1", name: "Riverside",
    polygon: [[40, 400], [340, 400], [340, 700], [40, 700]],
    population: 12000, flood_level: 0.68, elevation: 0.12, elevation_band: "LOW",
  },
  {
    id: "Z2", name: "Midtown",
    polygon: [[360, 200], [630, 200], [630, 560], [360, 560]],
    population: 18000, flood_level: 0, elevation: 0.5, elevation_band: "MED",
  },
  {
    id: "Z3", name: "Highland",
    polygon: [[660, 40], [990, 40], [990, 300], [660, 300]],
    population: 6000, flood_level: 0, elevation: 0.88, elevation_band: "HIGH",
  },
];

function road(id: string, source: string, destination: string, status: Road["status"]): Road {
  return {
    id, source, destination, status,
    distance: 7.16, geometric_length: 6.8, detour_factor: 1.05,
    elevation_band: "LOW", flood_level: status === "SAFE" ? 0.1 : 0.68,
    damage_level: 0, failure_probability: status === "RISKY" ? 0.5 : 0,
    risk_score: 0, blocked: status === "BLOCKED",
  };
}

const roads: Road[] = [
  road("R17", "N5", "N10", "SAFE"),
  road("R1", "N1", "N5", "SAFE"),
  road("R19", "N10", "N12", "RISKY"),
];

const hospitals: Hospital[] = [
  {
    id: "H1", name: "Central General", node_id: "N12",
    total_beds: 48, available_beds: 12, total_icu: 8, available_icu: 2,
    status: "OPEN", has_icu: true,
  },
];

const shelters: Shelter[] = [
  {
    id: "S1", name: "Highland School", node_id: "N18",
    capacity: 400, occupancy: 0, safety_score: 0.95, status: "OPEN",
  },
];

const ambulances: Ambulance[] = [
  {
    id: "A1", node_id: "N1", position: null, capacity: 2, speed_kmh: 55,
    status: "AVAILABLE", assigned_emergency: null,
  },
];

const emergencies: Emergency[] = [
  {
    id: "E7", node_id: "N1", zone_id: "Z1", severity: "CRITICAL",
    people_affected: 9, patients: 3, medical_priority: 5,
    reported_at_tick: 180, waiting_ticks: 0, status: "REPORTED",
    assigned_ambulance: null, assigned_hospital: null,
  },
];

function renderMap(overrides: Partial<Parameters<typeof DisasterMap>[0]> = {}) {
  return render(
    <DisasterMap
      nodes={nodes}
      zones={zones}
      roads={roads}
      hospitals={hospitals}
      shelters={shelters}
      ambulances={ambulances}
      emergencies={emergencies}
      {...overrides}
    />,
  );
}

/* -- rendering ------------------------------------------------------------ */

describe("rendering the world", () => {
  it("draws every node", () => {
    renderMap();
    for (const node of nodes) {
      expect(screen.getByTestId(`node-${node.id}`)).toBeTruthy();
    }
  });

  it("draws every road", () => {
    renderMap();
    for (const r of roads) {
      expect(screen.getByTestId(`road-${r.id}`)).toBeTruthy();
    }
  });

  it("draws every zone", () => {
    renderMap();
    for (const zone of zones) {
      expect(screen.getByTestId(`zone-${zone.id}`)).toBeTruthy();
    }
  });

  it("marks hospitals and shelters with distinct shapes", () => {
    renderMap();
    expect(screen.getByTestId("hospital-N12").tagName.toLowerCase()).toBe("rect");
    expect(screen.getByTestId("shelter-N18").tagName.toLowerCase()).toBe("polygon");
  });

  it("marks the node where an emergency is reported", () => {
    renderMap();
    expect(screen.getByTestId("emergency-at-N1")).toBeTruthy();
  });

  it("marks nodes holding an ambulance", () => {
    renderMap();
    expect(screen.getByTestId("ambulance-at-N1")).toBeTruthy();
  });

  it("does not mark nodes with no ambulance or emergency", () => {
    renderMap();
    expect(screen.queryByTestId("emergency-at-N10")).toBeNull();
    expect(screen.queryByTestId("ambulance-at-N10")).toBeNull();
  });

  it("skips roads whose endpoints are missing rather than crashing", () => {
    renderMap({ roads: [...roads, road("RX", "N1", "GHOST", "SAFE")] });
    expect(screen.queryByTestId("road-RX")).toBeNull();
    expect(screen.getByTestId("road-R17")).toBeTruthy();
  });
});

/* -- road status, the thing Phase 3 must demonstrate ---------------------- */

describe("road status", () => {
  it("exposes each road's status in the DOM", () => {
    renderMap();
    expect(screen.getByTestId("road-R17").getAttribute("data-status")).toBe("SAFE");
    expect(screen.getByTestId("road-R19").getAttribute("data-status")).toBe("RISKY");
  });

  it("updates when the backend reports a road blocked", () => {
    // The Phase 3 acceptance criterion: a status change from the stream must
    // reach the map without a remount.
    const { rerender } = renderMap();
    expect(screen.getByTestId("road-R17").getAttribute("data-status")).toBe("SAFE");

    const afterBlock = roads.map((r) =>
      r.id === "R17" ? road("R17", "N5", "N10", "BLOCKED") : r,
    );
    rerender(
      <DisasterMap
        nodes={nodes} zones={zones} roads={afterBlock}
        hospitals={hospitals} shelters={shelters}
        ambulances={ambulances} emergencies={emergencies}
      />,
    );

    expect(screen.getByTestId("road-R17").getAttribute("data-status")).toBe("BLOCKED");
  });

  it("distinguishes blocked roads by dash pattern, not colour alone", () => {
    renderMap({ roads: [road("R17", "N5", "N10", "BLOCKED")] });
    const line = screen.getByTestId("road-R17");
    expect(line.getAttribute("stroke-dasharray")).toBeTruthy();
  });

  it("leaves safe roads undashed", () => {
    renderMap();
    expect(screen.getByTestId("road-R17").getAttribute("stroke-dasharray")).toBeNull();
  });

  it("counts road statuses in the legend", () => {
    renderMap({
      roads: [
        road("R1", "N1", "N5", "SAFE"),
        road("R17", "N5", "N10", "BLOCKED"),
        road("R19", "N10", "N12", "RISKY"),
      ],
    });
    expect(screen.getByText("Blocked 1")).toBeTruthy();
    expect(screen.getByText("Risky 1")).toBeTruthy();
    expect(screen.getByText("Safe 1")).toBeTruthy();
  });
});

/* -- flood shading -------------------------------------------------------- */

describe("flood overlay", () => {
  it("shades a flooded zone in proportion to its flood_level", () => {
    renderMap();
    const overlay = screen.getByTestId("flood-Z1");
    expect(Number(overlay.getAttribute("opacity"))).toBeCloseTo(0.68 * 0.55, 5);
  });

  it("draws no overlay for a dry zone", () => {
    renderMap();
    expect(screen.queryByTestId("flood-Z2")).toBeNull();
  });

  it("deepens as flood_level rises", () => {
    const { rerender } = renderMap();
    const before = Number(screen.getByTestId("flood-Z1").getAttribute("opacity"));

    rerender(
      <DisasterMap
        nodes={nodes}
        zones={zones.map((z) => (z.id === "Z1" ? { ...z, flood_level: 1 } : z))}
        roads={roads} hospitals={hospitals} shelters={shelters}
        ambulances={ambulances} emergencies={emergencies}
      />,
    );
    expect(
      Number(screen.getByTestId("flood-Z1").getAttribute("opacity")),
    ).toBeGreaterThan(before);
  });
});

/* -- interaction ---------------------------------------------------------- */

describe("interaction", () => {
  it("shows a node's name on hover", () => {
    renderMap();
    expect(screen.queryByTestId("hover-label")).toBeNull();
    fireEvent.mouseEnter(screen.getByTestId("node-N1"));
    expect(screen.getByTestId("hover-label").textContent).toBe("Riverside Quay");
  });

  it("opens a detail panel with real backend fields when a road is clicked", () => {
    renderMap();
    fireEvent.click(screen.getByTestId("road-R17").previousElementSibling!);
    expect(screen.getByTestId("detail-kind").textContent).toBe("Road R17");
    expect(screen.getByText("7.16 km")).toBeTruthy();
    expect(screen.getByText("1.050")).toBeTruthy();
  });

  it("shows hospital capacity when a hospital node is clicked", () => {
    renderMap();
    fireEvent.click(screen.getByTestId("node-N12"));
    expect(screen.getByText("Central General")).toBeTruthy();
    expect(screen.getByText("12 / 48")).toBeTruthy();
    expect(screen.getByText("2 / 8")).toBeTruthy();
  });

  it("shows emergency detail when an emergency site is clicked", () => {
    renderMap();
    fireEvent.click(screen.getByTestId("node-N1"));
    expect(screen.getByTestId("detail-kind").textContent).toBe("Emergency site");
    expect(screen.getByText("9 (3 patients)")).toBeTruthy();
  });

  it("closes the panel when the same entity is clicked twice", () => {
    renderMap();
    fireEvent.click(screen.getByTestId("node-N12"));
    // Queried by test id, not by text: "Hospital" also appears in the legend,
    // so getByText would match the wrong element and pass for the wrong reason.
    expect(screen.getByTestId("detail-kind").textContent).toBe("Hospital");
    fireEvent.click(screen.getByTestId("node-N12"));
    expect(screen.queryByTestId("map-detail-panel")).toBeNull();
  });

  it("offers zoom controls", () => {
    renderMap();
    expect(screen.getByLabelText("Zoom in")).toBeTruthy();
    expect(screen.getByLabelText("Zoom out")).toBeTruthy();
    expect(screen.getByLabelText("Reset view")).toBeTruthy();
  });

  it("zooming in narrows the viewBox", () => {
    const { container } = renderMap();
    const svg = container.querySelector("svg")!;
    expect(svg.getAttribute("viewBox")).toBe("0 0 1000 700");

    fireEvent.click(screen.getByLabelText("Zoom in"));
    const [, , width] = svg.getAttribute("viewBox")!.split(" ").map(Number);
    expect(width).toBeLessThan(1000);
  });

  it("reset returns to the full world view", () => {
    const { container } = renderMap();
    const svg = container.querySelector("svg")!;
    fireEvent.click(screen.getByLabelText("Zoom in"));
    fireEvent.click(screen.getByLabelText("Zoom in"));
    expect(svg.getAttribute("viewBox")).not.toBe("0 0 1000 700");

    fireEvent.click(screen.getByLabelText("Reset view"));
    expect(svg.getAttribute("viewBox")).toBe("0 0 1000 700");
  });

  it("disables zoom out at full extent", () => {
    renderMap();
    expect(screen.getByLabelText("Zoom out").hasAttribute("disabled")).toBe(true);
  });
});

/* -- static embed --------------------------------------------------------- */

describe("static mode (the dashboard embed)", () => {
  it("renders the same entities", () => {
    renderMap({ interactive: false });
    expect(screen.getByTestId("node-N1")).toBeTruthy();
    expect(screen.getByTestId("road-R17")).toBeTruthy();
  });

  it("hides the zoom controls", () => {
    renderMap({ interactive: false });
    expect(screen.queryByLabelText("Zoom in")).toBeNull();
  });

  it("does not respond to hover", () => {
    renderMap({ interactive: false });
    fireEvent.mouseEnter(screen.getByTestId("node-N1"));
    expect(screen.queryByTestId("hover-label")).toBeNull();
  });

  it("does not open a detail panel on click", () => {
    renderMap({ interactive: false });
    fireEvent.click(screen.getByTestId("node-N12"));
    expect(screen.queryByTestId("map-detail-panel")).toBeNull();
  });

  it("still shows the legend, so road colour remains readable", () => {
    renderMap({ interactive: false });
    expect(screen.getByText("Blocked 0")).toBeTruthy();
  });
});

/* -- degenerate input ----------------------------------------------------- */

describe("empty and partial data", () => {
  it("renders with no emergencies or ambulances", () => {
    renderMap({ emergencies: [], ambulances: [] });
    expect(screen.getByTestId("node-N1")).toBeTruthy();
    expect(screen.queryByTestId("emergency-at-N1")).toBeNull();
  });

  it("renders before the first snapshot arrives", () => {
    const { container } = renderMap({
      nodes: [], zones: [], roads: [],
      hospitals: [], shelters: [], ambulances: [], emergencies: [],
    });
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
