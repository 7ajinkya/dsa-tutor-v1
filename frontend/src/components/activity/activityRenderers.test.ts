import { createSSRApp } from "vue";
import { renderToString } from "@vue/server-renderer";
import { describe, expect, it } from "vitest";
import type { Activity } from "../../api/types";
import CodeWritingRenderer from "./CodeWritingRenderer.vue";
import ComplexityRenderer from "./ComplexityRenderer.vue";
import FreeFormRenderer from "../FreeFormRenderer.vue";
import GraphConstructionRenderer from "./GraphConstructionRenderer.vue";
import LinesRenderer from "./LinesRenderer.vue";
import McqRenderer from "./McqRenderer.vue";

const base: Activity = {
  id: "activity", type: "mcq", mode: "assess", purpose: "Server purpose",
  prompt: "Server prompt", answer_format: "letter", position: { index: 2, of: 4 },
  unit: null, skill: { id: "skill", title: "Skill" }, choices: [{ id: "a", text: "Choice" }],
  code: "print('x')", starter: "def solve():", function_name: "solve", nodes: ["A", "B"],
  kind: "sum", generated: true, hints: { allowed: false, max_level: 0 }, available_actions: ["answer"],
};

async function html(component: object, activity: Activity): Promise<string> {
  return renderToString(createSSRApp(component, { activity, busy: false, error: null }));
}

describe("C6 activity renderers", () => {
  it.each([
    ["mcq", McqRenderer, "Choice"], ["free_form", FreeFormRenderer, "textarea"],
    ["output_prediction", LinesRenderer, "print"], ["code_tracing", LinesRenderer, "print"],
    ["complexity_question", ComplexityRenderer, "Big-O answer"],
    ["code_writing", CodeWritingRenderer, "solve"], ["graph_construction", GraphConstructionRenderer, "A"],
  ])("renders the %s payload", async (type, component, expected) => {
    const result = await html(component, { ...base, type });
    expect(result).toContain(expected);
    expect(result).toContain("Server purpose");
    expect(result).toContain("assess");
  });

  it("renders loading and API error states through the shared frame", async () => {
    const result = await renderToString(createSSRApp(McqRenderer, {
      activity: base, busy: true, error: "Storage unavailable",
    }));
    expect(result).toContain("disabled");
    expect(result).toContain("Storage unavailable");
  });
});
