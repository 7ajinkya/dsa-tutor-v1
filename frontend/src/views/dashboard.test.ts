import { describe, expect, it } from "vitest";
import { groupByModule, hasProgressEvidence, homeScope, homeSessionAction } from "./dashboard";
import type { HomePayload, PlanRow } from "../api/types";

const home: HomePayload = {
  daily: { target_units: 4, completed_units: 1, status: "active" },
  plan: { items: [], mastered: 1, pace_budget: "normal", questions: 3,
    remaining_minutes: 24, theory_blocks: 1, total_skills: 38, units: 2 },
  progress_summary: { mastered: 1, total_skills: 38 },
  resume: { available: false, session_id: null, pace: null },
};

const row = (module: string, evidence: number): PlanRow => ({
  skill: `${module}-${evidence}`, title: "Skill", section: "Foundations", module,
  state: "NOT_SEEN", evidence, mastered: false, boundary: false, optional: false,
});

describe("dashboard display helpers", () => {
  it("labels expected scope only from the server plan", () => {
    expect(homeScope(home)).toBe("3 expected checks across 2 planned units");
    expect(homeScope({ ...home, plan: { ...home.plan, units: 0, questions: 0 } }))
      .toContain("learning engine");
  });

  it("uses mutually exclusive start or resume actions from the server response", () => {
    expect(homeSessionAction(home)).toEqual({ kind: "start" });
    expect(homeSessionAction({ ...home, resume: { available: true, session_id: 7, pace: "fast" } }))
      .toEqual({ kind: "resume", sessionId: 7 });
    expect(homeSessionAction({ ...home, resume: { available: true, session_id: null, pace: null } }))
      .toEqual({ kind: "start" });
  });

  it("recognizes the before-first-session progress state", () => {
    expect(hasProgressEvidence([row("A", 0)])).toBe(false);
    expect(hasProgressEvidence([row("A", 0), row("B", 1)])).toBe(true);
  });

  it("groups the server's qualitative rows by their provided module", () => {
    const groups = groupByModule([row("A", 1), row("B", 1), row("A", 2)]);
    expect([...groups.keys()]).toEqual(["A", "B"]);
    expect(groups.get("A")).toHaveLength(2);
  });
});
