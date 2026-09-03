import { describe, expect, it } from "vitest";
import { currentSessionMatches, defensiveTurnLabel, routeSessionId, theoryScope } from "./sessionView";
import type { SessionInfo, TurnEnvelope } from "../api/types";

const session: SessionInfo = {
  id: 3, status: "active", pace: "normal", budget_minutes: 25, remaining_minutes: 20,
  started_at: null, ended_at: null, end_reason_code: null, end_reason_detail: null, daily: null,
};
const turn: TurnEnvelope = {
  type: "activity", session, step: null, notice: null, theory: null, result: null, hint: null,
  activity: {
    id: "future-turn", type: "free_form", mode: "assess", purpose: "Server purpose",
    prompt: "Server prompt", answer_format: "text", position: null, unit: null,
    skill: { id: "skill", title: "Skill" }, choices: null, code: null, starter: null,
    function_name: null, nodes: null, kind: null, generated: false,
    hints: { allowed: false, max_level: 0 }, available_actions: [],
  },
};

describe("C5 session display helpers", () => {
  it("validates route ids without inventing a session", () => {
    expect(routeSessionId("3")).toBe(3);
    expect(routeSessionId("abc")).toBeNull();
    expect(routeSessionId(undefined)).toBeNull();
  });

  it("checks only authoritative session identity", () => {
    expect(currentSessionMatches(session, 3)).toBe(true);
    expect(currentSessionMatches(session, 4)).toBe(false);
    expect(currentSessionMatches(null, 3)).toBe(false);
  });

  it("describes non-theory turns defensively using server metadata", () => {
    expect(defensiveTurnLabel(turn)).toBe("The server provided a free_form turn in assess mode.");
  });

  it("communicates theory scope without choosing the next interaction", () => {
    expect(theoryScope({ unit: { id: "u", title: "Theory", goal: "Goal" }, text: "Text", checks_upcoming: 2 }))
      .toBe("2 checks expected after acknowledgement");
  });
});


import { endedSummary } from "./sessionView";

describe("C8 ended-session summary (authoritative, no recovery prompts)", () => {
  const endedTurn = {
    type: "ended" as const, session: null, step: null, notice: null,
    activity: null, theory: null, result: null, hint: null,
  };
  const endedTurnWithNotice = {
    ...endedTurn,
    notice: { kind: "ended", text: "Session paused - state persisted (learner requested stop)." },
  };

  it("renders an ended session as ended with no resume CTA", () => {
    const summary = endedSummary(endedTurn, { status: "completed" });
    expect(summary.badge).toBe("ended");
    expect(summary.showResumeCta).toBe(false);
  });

  it("renders a paused session with the resume CTA available", () => {
    const summary = endedSummary(endedTurnWithNotice, { status: "paused" });
    expect(summary.badge).toBe("paused");
    expect(summary.showResumeCta).toBe(true);
  });

  it("prefers the server notice text as the detail", () => {
    const summary = endedSummary(endedTurnWithNotice, { status: "paused" });
    expect(summary.detail).toBe("Session paused - state persisted (learner requested stop).");
  });

  it("falls back to a neutral detail when the server sends none", () => {
    const summary = endedSummary(endedTurn, { status: "completed" });
    expect(summary.detail).toBe("The session is no longer active.");
  });
});
