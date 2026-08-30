import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FOLPanel } from "@/components/knowledge/FOLPanel";
import type { FOLResult } from "@/types";

const result: FOLResult = {
  query: "Unsafe(R) & Road(R)",
  bindings: [{ R: "R17" }, { R: "R22" }],
  count: 2,
  execution_ms: 0.12,
};

describe("FOLPanel", () => {
  it("renders bindings returned by the knowledge engine", () => {
    render(<FOLPanel result={result} onQuery={vi.fn()} pending={false} />);
    expect(screen.getByText("R17")).toBeTruthy();
    expect(screen.getByText("R22")).toBeTruthy();
    expect(screen.getByText(/2 matches/)).toBeTruthy();
  });

  it("submits the edited query", async () => {
    const user = userEvent.setup();
    const onQuery = vi.fn();
    render(<FOLPanel result={null} onQuery={onQuery} pending={false} />);
    const input = screen.getByRole("textbox", { name: "FOL query" });
    await user.clear(input);
    await user.type(input, "PriorityRescue(E)");
    await user.click(screen.getByRole("button", { name: "Query" }));
    expect(onQuery).toHaveBeenCalledWith("PriorityRescue(E)");
  });
});
