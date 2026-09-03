import { describe, expect, it } from "vitest";
import { rendererForType } from "./rendererContract";

describe("activity dispatcher contract", () => {
  it.each([
    ["mcq", "mcq"], ["free_form", "free_form"],
    ["output_prediction", "lines"], ["code_tracing", "lines"],
    ["complexity_question", "complexity_question"],
    ["code_writing", "code_writing"], ["graph_construction", "graph_construction"],
  ])("selects the renderer for %s without changing its intent", (type, expected) => {
    expect(rendererForType(type)).toBe(expected);
  });

  it("uses a neutral fallback for unknown types", () => {
    expect(rendererForType("future_activity")).toBe("unknown");
  });
});
