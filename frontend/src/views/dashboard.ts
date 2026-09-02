import type { HomePayload, PlanRow } from "../api/types";

/** Display-only helpers for C4. They group and label server-provided data;
 * they make no progression or mastery decisions. */
export function homeScope(home: HomePayload): string {
  const units = home.plan.units;
  const questions = home.plan.questions;
  if (units > 0 && questions > 0) {
    return `${questions} expected check${questions === 1 ? "" : "s"} across ${units} planned unit${units === 1 ? "" : "s"}`;
  }
  if (units > 0) return `${units} planned unit${units === 1 ? "" : "s"}; the engine will provide the activity scope`;
  return "Your next activity will be selected by the learning engine";
}

export type HomeSessionAction =
  | { kind: "start" }
  | { kind: "resume"; sessionId: number };

/** The CTA only follows the server's resume flag and session id. */
export function homeSessionAction(home: HomePayload): HomeSessionAction {
  return home.resume.available && home.resume.session_id !== null
    ? { kind: "resume", sessionId: home.resume.session_id }
    : { kind: "start" };
}

export function hasProgressEvidence(rows: PlanRow[]): boolean {
  return rows.some((row) => row.evidence > 0);
}

export function groupByModule(rows: PlanRow[]): Map<string, PlanRow[]> {
  const groups = new Map<string, PlanRow[]>();
  for (const row of rows) {
    const group = groups.get(row.module) ?? [];
    group.push(row);
    groups.set(row.module, group);
  }
  return groups;
}
