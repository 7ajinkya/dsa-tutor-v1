import type { SessionInfo, Theory, TurnEnvelope } from "../api/types";

export function routeSessionId(rawId: string | string[] | undefined): number | null {
  const value = Array.isArray(rawId) ? rawId[0] : rawId;
  if (!value || !/^\d+$/.test(value)) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

export function currentSessionMatches(session: SessionInfo | null, id: number): boolean {
  return session?.id === id;
}

/** C5 renders metadata for future turn types without selecting an interaction UI. */
export function defensiveTurnLabel(turn: TurnEnvelope): string {
  if (turn.type === "activity" && turn.activity) {
    return `The server provided a ${turn.activity.type} turn${turn.activity.mode ? ` in ${turn.activity.mode} mode` : ""}.`;
  }
  if (turn.type === "ended") return "The server has ended this session turn.";
  if (turn.type === "notice") return turn.notice?.text ?? "The server provided a session notice.";
  return "The server provided a turn that is ready to render.";
}

export interface EndedSummary {
  badge: string;
  reasonCode: string | null;
  detail: string;
  showResumeCta: boolean;
}

/** C8: renders the authoritative ended state without offering recovery
 *  prompts — the session stays ended (design §5.4). The reason code is the
 *  server-provided `end_reason_code`, passed through verbatim. */
export function endedSummary(turn: TurnEnvelope, session: { status: string;
  end_reason_code?: string | null } | null): EndedSummary {
  const code = session?.status === "paused" ? "paused" : "ended";
  const detail = turn.notice?.text ?? "The session is no longer active.";
  return {
    badge: code,
    reasonCode: session?.end_reason_code ?? null,
    detail,
    showResumeCta: code === "paused",
  };
}

export function theoryScope(theory: Theory): string {
  return `${theory.checks_upcoming} check${theory.checks_upcoming === 1 ? "" : "s"} expected after acknowledgement`;
}
