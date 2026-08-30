/**
 * HMM panel DOM tests.
 *
 * The panel must never present ground truth as an inference, and must show the
 * lag between the two rather than hiding it.
 */

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { BayesianNetwork } from "@/components/probability/BayesianNetwork";
import { HMMPanel } from "@/components/probability/HMMPanel";
import type { BayesianResponse, HMMResponse } from "@/types";

afterEach(cleanup);

const hmm: HMMResponse = {
  belief: { NORMAL: 0.006, RISING: 0.162, HIGH: 0.632, CRITICAL: 0.201 },
  most_likely: "HIGH",
  entropy: 1.35,
  step_likelihood: 0.42,
  observation_history: ["LOW_WATER", "MEDIUM_WATER", "HIGH_WATER"],
  belief_history: [
    [0.9, 0.08, 0.02, 0],
    [0.6, 0.35, 0.05, 0],
    [0.006, 0.162, 0.632, 0.201],
  ],
  states: ["NORMAL", "RISING", "HIGH", "CRITICAL"],
  live: true,
  execution_ms: 0,
};

describe("HMM panel", () => {
  it("renders a bar for every hidden state", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="CRITICAL" />);
    for (const state of hmm.states) {
      expect(screen.getByTestId(`hmm-bar-${state}`)).toBeTruthy();
    }
  });

  it("shows each probability as a percentage", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="CRITICAL" />);
    expect(screen.getByText("63.2%")).toBeTruthy();
    expect(screen.getByText("20.1%")).toBeTruthy();
  });

  it("bar width tracks the probability", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="CRITICAL" />);
    const high = screen.getByTestId("hmm-bar-HIGH") as HTMLElement;
    const normal = screen.getByTestId("hmm-bar-NORMAL") as HTMLElement;
    expect(high.style.width).toBe("63%");
    expect(normal.style.width).toBe("1%");
  });

  it("reports uncertainty in bits", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="CRITICAL" />);
    expect(screen.getByText("1.35 bits")).toBeTruthy();
  });

  it("calls out the lag when belief disagrees with ground truth", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="CRITICAL" />);
    const note = screen.getByTestId("hmm-lag-note").textContent ?? "";
    expect(note).toContain("HIGH");
    expect(note).toContain("CRITICAL");
    expect(note.toLowerCase()).toContain("lag");
  });

  it("says so when belief agrees, without claiming it always will", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="HIGH" />);
    const note = screen.getByTestId("hmm-lag-note").textContent ?? "";
    expect(note.toLowerCase()).toContain("agrees");
    expect(note.toLowerCase()).toContain("not always");
  });

  it("labels ground truth as never being an input to a decision", () => {
    render(<HMMPanel hmm={hmm} trueFloodState="HIGH" />);
    expect(
      screen.getByText(/never an input to any decision/i),
    ).toBeTruthy();
  });

  it("renders a loading state rather than fabricating numbers", () => {
    render(<HMMPanel hmm={null} trueFloodState="NORMAL" />);
    expect(screen.getByText(/Loading belief/i)).toBeTruthy();
    expect(screen.queryByTestId("hmm-belief")).toBeNull();
  });
});

const bayes: BayesianResponse = {
  flood_severity: { NORMAL: 0.02, RISING: 0.1, HIGH: 0.38, CRITICAL: 0.5 },
  water_level: { LOW: 0, MED: 0, HIGH: 1 },
  rainfall: { LOW: 0, MED: 0, HIGH: 1 },
  per_road: { R17: 0.908, R1: 0.799 },
  evidence: { Rainfall: "HIGH", WaterLevel: "HIGH" },
  used_hmm_virtual_evidence: true,
  execution_ms: 1.23,
  riskiest_roads: [
    { road_id: "R17", probability: 0.908, elevation_band: "LOW" },
  ],
};

describe("Bayesian network panel", () => {
  it("shows the posterior over flood severity", () => {
    render(<BayesianNetwork bayes={bayes} />);
    expect(screen.getByTestId("bn-severity")).toBeTruthy();
    expect(screen.getByText("50.0%")).toBeTruthy();
  });

  it("labels the evidence actually used", () => {
    render(<BayesianNetwork bayes={bayes} />);
    expect(screen.getAllByText("= HIGH").length).toBe(2);
  });

  it("marks the HMM virtual evidence when attached", () => {
    render(<BayesianNetwork bayes={bayes} />);
    // Matched exactly: /HMM/ also hits the explanatory paragraph below the
    // diagram, so a loose query would pass for the wrong reason.
    expect(screen.getByText("HMM \u03bb(s)")).toBeTruthy();
    expect(screen.queryByText("HMM detached")).toBeNull();
  });

  it("marks the HMM as detached in what-if mode", () => {
    render(
      <BayesianNetwork bayes={{ ...bayes, used_hmm_virtual_evidence: false }} />,
    );
    expect(screen.getByText("HMM detached")).toBeTruthy();
  });

  it("explains the two pathways", () => {
    render(<BayesianNetwork bayes={bayes} />);
    expect(screen.getByText(/without passing through/i)).toBeTruthy();
  });

  it("reports inference time rather than implying it is free", () => {
    render(<BayesianNetwork bayes={bayes} />);
    expect(screen.getByText(/1\.23 ms/)).toBeTruthy();
  });

  it("renders a loading state when there is no result", () => {
    render(<BayesianNetwork bayes={null} />);
    expect(screen.getByText(/Running inference/i)).toBeTruthy();
  });
});
