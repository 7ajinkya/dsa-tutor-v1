/**
 * C10 (plan A20 L3 / A22): Playwright learner journeys against the REAL V1 API.
 *
 * Ground rules (from the C10 instructions + plan):
 * - The server decides mode/purpose/ordering/available_actions; these tests only
 *   observe and interact. No hardcoded THEORY->MCQ->PROBLEM pedagogy sequence.
 * - Deterministic outcomes come from the frozen V0 curriculum content
 *   (dsa_tutor/content/curriculum_v0.py) and the deterministic builtin provider
 *   (dsa_tutor/ai/builtin_provider.py), probed via the real API while writing
 *   these journeys. Fixture knowledge used: correct MCQ choices per skill title,
 *   the failure ladder (1st failure -> generated remediation), the generic
 *   hint ladder (5 served hints, then 409 LADDER_EXHAUSTED), and the remediation
 *   fallback for unbanked skills (free_form "explain ... in one sentence",
 *   graded correct on any non-empty answer because open_ended=true).
 * - The backend is the genuine FastAPI app in --offline mode (MemoryStorage,
 *   fresh per run): no API mocking. The single route interception in the
 *   retryable-failure journey simulates a network failure, which is the
 *   scenario under test; the retry goes to the real server.
 * - One serial session lifecycle: journeys continue where the previous ended.
 */
import { expect, test, type Page } from "@playwright/test";

test.describe.configure({ mode: "serial" });

let sessionId = 1;

const CORRECT_BY_SKILL: Array<[string, string]> = [
  ["What is a graph?", "a"],
  ["Adjacency", "a"],
  ["Vertices and edges", "a"],
  ["course-prerequisite", "a"],
];
const WRONG_BY_SKILL: Array<[string, string]> = [
  ["What is a graph?", "d"],
  ["Adjacency", "d"],
  ["Vertices and edges", "d"],
  ["course-prerequisite", "d"],
];
/** The remediation fallback for unbanked skills is free_form and open-ended:
 *  any non-empty answer grades correct (builtin_provider.grade_free_form). */
const FREE_FORM_ANSWER = "A graph is a set of vertices connected by edges to show relationships.";

async function currentPurpose(page: Page): Promise<string> {
  return (await page.locator(".activity-purpose").textContent()) ?? "";
}

function choiceLetterFor(purpose: string, table: Array<[string, string]>): string {
  for (const [needle, letter] of table) {
    if (purpose.includes(needle)) return letter;
  }
  return "a"; // unknown (e.g. generated remediation): neutral first choice
}

/** Answer whatever the engine currently serves: radios for MCQs, the open
 *  textarea for free-form. Returns the interaction type actually answered. */
async function answerCurrent(page: Page, letter: string): Promise<"mcq" | "free_form"> {
  const radioCount = await page.locator('.activity-card input[type="radio"]').count();
  if (radioCount > 0) {
    await page.locator(`input[type="radio"][value="${letter}"]`).check();
    await submitAnswer(page);
    return "mcq";
  }
  await page.locator(".activity-card textarea").first().fill(FREE_FORM_ANSWER);
  await submitAnswer(page);
  return "free_form";
}

async function selectChoice(page: Page, letter: string): Promise<void> {
  await page.locator(`input[type="radio"][value="${letter}"]`).check();
}

async function submitAnswer(page: Page): Promise<void> {
  await page.getByRole("button", { name: /submit answer/i }).click();
}

test.describe("C10 learner journeys (serial, real V1 API)", () => {
  test("J1: home -> start session -> theory -> acknowledge -> first activity", async ({ page }) => {
    const pageErrors: string[] = [];
    page.on("pageerror", (error) => pageErrors.push(String(error)));

    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Continue your DSA learning" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Start session" })).toBeVisible();

    await page.getByRole("button", { name: "Start session" }).click();
    await expect(page).toHaveURL(/\/session\/\d+$/);
    sessionId = Number(new URL(page.url()).pathname.split("/").pop());
    expect(sessionId).toBeGreaterThan(0);

    // Theory turn: server-provided unit + read gate.
    await expect(page.locator(".theory-panel")).toBeVisible();
    await expect(page.getByRole("button", { name: /read this/i })).toBeVisible();
    await page.getByRole("button", { name: /read this/i }).click();

    // Authoritative next turn: an activity selected by the engine.
    await expect(page.locator(".activity-card")).toBeVisible();
    const purpose = await currentPurpose(page);
    expect(purpose.length).toBeGreaterThan(0);
    await expect(page.getByRole("button", { name: /submit answer/i })).toBeEnabled();

    // Recovery/ended surfaces are NOT shown on an active session.
    await expect(page.locator(".turn-ended")).toHaveCount(0);
    expect(pageErrors).toEqual([]);
  });

  test("J2: hint ladder -> exhaustion -> reveal confirmation -> reveal", async ({ page }) => {
    await page.goto(`/session/${sessionId}`);
    await expect(page.locator(".activity-card")).toBeVisible();

    await page.locator(".hint-toggle-btn").click();
    await expect(page.locator(".hint-drawer")).toBeVisible();
    await expect(page.locator(".hint-toggle-btn")).toHaveAttribute("aria-expanded", "true");

    await page.locator(".get-first-hint-btn").click();
    await expect(page.locator(".active-hint-card")).toBeVisible();
    // Climb the ladder until the server reports exhaustion (409 LADDER_EXHAUSTED).
    // The rung count is server-owned (authored or generic ladder): keep clicking
    // while the "next hint" button exists and the exhausted card has not settled.
    await expect(async () => {
      const exhaustedCard = page.locator(".ladder-exhausted-card");
      if (await exhaustedCard.isVisible()) {
        await expect(exhaustedCard).toBeVisible();
        return;
      }
      await page.locator(".next-hint-btn").click({ timeout: 2_000 });
      await expect(exhaustedCard).toBeVisible({ timeout: 2_000 });
    }).toPass({ timeout: 20_000 });
    await expect(page.locator(".ladder-exhausted-card")).toBeVisible();
    await expect(page.locator(".reveal-cta-btn")).toBeVisible();

    // C9 regression: Escape cancels the confirmation dialog without revealing.
    // (The drawer's own C9 Escape handling also dismisses the drawer.)
    await page.locator(".reveal-cta-btn").click();
    await expect(page.locator(".confirm-modal-backdrop")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.locator(".confirm-modal-backdrop")).toHaveCount(0);
    await expect(page.locator(".solution-inset")).toHaveCount(0);

    // Confirm for real: reopen the drawer and reveal. The exhausted card persists
    // (isExhausted is activity-scoped), so the CTA is still offered.
    await page.locator(".hint-toggle-btn").click();
    await expect(page.locator(".ladder-exhausted-card")).toBeVisible();
    await page.locator(".reveal-cta-btn").click();
    await expect(page.locator(".confirm-modal-backdrop")).toBeVisible();
    await page.locator(".confirm-accept-btn").click();
    await expect(page.locator(".solution-inset")).toBeVisible();
    await expect(page.locator(".solution-inset")).toContainText("Assisted attempt");
  });

  test("J3: wrong answer -> result feedback -> authoritative next turn", async ({ page }) => {
    await page.goto(`/session/${sessionId}`);
    const purpose = await currentPurpose(page);
    await selectChoice(page, choiceLetterFor(purpose, WRONG_BY_SKILL));
    await submitAnswer(page);

    const resultCard = page.locator(".result-card");
    await expect(resultCard).toBeVisible();
    await expect(resultCard).toContainText("Not quite");
    await expect(resultCard).toContainText("Answered by");

    // First failure -> the struggle ladder: a generated remediation activity.
    await expect(page.locator(".activity-card")).toHaveCount(1);
    const nextPurpose = await currentPurpose(page);
    expect(nextPurpose.length).toBeGreaterThan(0);
    await expect(page.getByRole("button", { name: /submit answer/i })).toBeEnabled();
  });

  test("J4: keyboard-only interaction on the current activity", async ({ page }) => {
    await page.goto(`/session/${sessionId}`);
    await expect(page.locator(".activity-card")).toBeVisible();

    // Walk tabs until a radio answer input is focused (bounded; no trap).
    let focusedRadio = false;
    for (let tab = 0; tab < 20 && !focusedRadio; tab += 1) {
      await page.keyboard.press("Tab");
      focusedRadio = await page.evaluate(
        () => (document.activeElement as HTMLInputElement | null)?.type === "radio",
      );
    }
    expect(focusedRadio, "a radio choice should be reachable via keyboard").toBe(true);

    // Radio group keyboard behavior: arrow moves the selection.
    await page.keyboard.press("ArrowDown");
    const checked = await page.evaluate(
      () => (document.querySelector('input[type="radio"]:checked') as HTMLInputElement | null)?.value ?? "",
    );
    expect(checked.length).toBeGreaterThan(0);

    // Walk tabs to the submit button and activate with Enter.
    let focusedSubmit = false;
    for (let tab = 0; tab < 12 && !focusedSubmit; tab += 1) {
      await page.keyboard.press("Tab");
      focusedSubmit = await page.evaluate(() => {
        const el = document.activeElement as HTMLButtonElement | null;
        return el?.tagName === "BUTTON" && el.type === "submit";
      });
    }
    expect(focusedSubmit, "the submit button should be reachable via keyboard").toBe(true);
    await page.keyboard.press("Enter");

    await expect(page.locator(".result-card").first()).toBeVisible();
  });

  test("J5: stale submission adopts the authoritative server turn (two pages)", async ({ page }) => {
    await page.goto(`/session/${sessionId}`);
    await expect(page.locator(".activity-card")).toBeVisible();
    const purposeBefore = await currentPurpose(page);

    // A second page holds the same, now-stale view of the session.
    const page2 = await page.context().newPage();
    await page2.goto(`/session/${sessionId}`);
    await expect(page2.locator(".activity-purpose")).toHaveText(purposeBefore);

    // Page 1 advances the session; page 2 still shows the old activity.
    await answerCurrent(page, choiceLetterFor(purposeBefore, CORRECT_BY_SKILL));
    await expect(page.locator(".result-card").first()).toBeVisible();
    const purposeAfter = await currentPurpose(page);

    // Page 2 submits against the stale activity: 409 STALE_ACTIVITY -> adopt.
    if (await page2.locator('.activity-card input[type="radio"]').count() > 0) {
      await selectChoice(page2, "a");
    }
    await submitAnswer(page2);
    await expect(page2.locator(".toast")).toContainText("Skipped ahead");
    await expect(page2.locator(".activity-purpose").last()).toHaveText(purposeAfter!);
    // The stale answer was never re-submitted: no result card appears on page 2.
    await expect(page2.locator(".result-card")).toHaveCount(0);
    await page2.close();
  });

  test("J6: retryable failure keeps the answer and retries with the same idempotency key", async ({ page }) => {
    await page.goto(`/session/${sessionId}`);
    await expect(page.locator(".activity-card")).toBeVisible();

    const keys: string[] = [];
    let calls = 0;
    const answerPattern = /\/api\/v1\/sessions\/\d+\/activities\/[^/]+\/answer$/;
    await page.route(answerPattern, async (route) => {
      if (route.request().method() !== "POST") return route.continue();
      calls += 1;
      keys.push(route.request().headers()["idempotency-key"] ?? "");
      if (calls === 1) await route.abort("connectionreset");
      else await route.continue();
    });

    const purpose = await currentPurpose(page);
    await answerCurrent(page, choiceLetterFor(purpose, CORRECT_BY_SKILL));

    // First attempt died at the network layer: the recovery state is visible.
    await expect(page.getByRole("button", { name: "Retry answer" })).toBeVisible();
    await page.getByRole("button", { name: "Retry answer" }).click();

    // The retry reaches the real server and lands an authoritative result.
    await expect(page.locator(".result-card").first()).toBeVisible();
    await page.unroute(answerPattern);

    expect(calls).toBe(2);
    expect(keys[0]).not.toBe("");
    // C8/C10 contract: the retry reused the SAME Idempotency-Key.
    expect(keys[1]).toBe(keys[0]);
  });

  test("J6b: HTTP 503 retryable failure shows recovery UI and retries successfully", async ({ page }) => {
    await page.goto(`/session/${sessionId}`);
    await expect(page.locator(".activity-card")).toBeVisible();

    const answerPattern = /\/api\/v1\/sessions\/\d+\/activities\/[^/]+\/answer$/;

    await page.route(answerPattern, async (route) => {
      if (route.request().method() !== "POST") {
        return route.continue();
      }

      await route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({
          error: {
            code: "STORAGE_UNAVAILABLE",
            message: "Storage is temporarily unavailable.",
            retryable: true,
          },
        }),
      });
    });

    const purpose = await currentPurpose(page);
    await answerCurrent(page, choiceLetterFor(purpose, CORRECT_BY_SKILL));

    // This is specifically an HTTP 503 response, not a network failure.
    await expect(page.getByRole("button", { name: "Retry answer" })).toBeVisible();
    await expect(page.locator(".result-card")).toHaveCount(0);

    // Remove the simulated failure. The retained submission should now be
    // retried against the real backend.
    await page.unroute(answerPattern);

    await page.getByRole("button", { name: "Retry answer" }).click();

    await expect(page.locator(".result-card").first()).toBeVisible();
    await expect(page.locator(".result-card").first()).toContainText("Answered by");
  });

  test("J7: mobile viewport journey (home -> session -> answer)", async ({ page }) => {
    // Explicit mobile viewport: the journey runs in every project, including the
    // desktop ones (Pixel 7 dimensions, C9 breakpoint <768).
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Continue your DSA learning" })).toBeVisible();

    // No horizontal overflow at 390px (C9 hardening holds up in a real browser).
    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(392);

    await expect(page.getByRole("button", { name: "Resume session" })).toBeVisible();
    await page.getByRole("button", { name: "Resume session" }).click();
    await expect(page).toHaveURL(new RegExp(`/session/${sessionId}$`));
    await expect(page.locator(".activity-card")).toBeVisible();

    await answerCurrent(page, choiceLetterFor(await currentPurpose(page), CORRECT_BY_SKILL));
    await expect(page.locator(".result-card").first()).toBeVisible();
  });

  test("J8: stop -> paused snapshot renders the authoritative turn -> resume", async ({ page }) => {
    // No Stop control exists in the UI (known C5 gap, deliberately not C10 scope):
    // stop through the real API, then observe what the server actually provides.
    // The request goes straight to the backend: the dev server has no /api proxy.
    const stopUrl = `http://127.0.0.1:8000/api/v1/sessions/${sessionId}/stop`;
    expect((await page.request.post(stopUrl, { data: {} })).ok()).toBeTruthy();
    // Retry-safe stop (design R5): pausing an already-paused session is a no-op.
    expect((await page.request.post(stopUrl, { data: {} })).ok()).toBeTruthy();

    // Reload: the route guard fetches the snapshot (zero server writes) and
    // renders the authoritative current turn — the frozen activity — while the
    // session facts report the paused status (plan §18: server is the storage).
    await page.goto(`/session/${sessionId}`);
    await expect(page.locator(".activity-card")).toBeVisible();
    await expect(page.locator(".session-facts")).toContainText("paused");

    // Resume entry per plan §18: home resume card -> POST resume -> the engine
    // resumes in place and the session is active again.
    await page.goto("/");
    await expect(page.getByRole("button", { name: "Resume session" })).toBeVisible();
    await page.getByRole("button", { name: "Resume session" }).click();
    await expect(page).toHaveURL(new RegExp(`/session/${sessionId}$`));
    await expect(page.locator(".activity-card")).toBeVisible();
    await expect(page.locator(".session-facts")).toContainText("active");
  });

  test("J9: disallowed origin does not receive an Access-Control-Allow-Origin header", async ({ request }) => {
    const response = await request.get("http://127.0.0.1:8000/api/v1/home", {
      headers: {
        Origin: "https://evil.example",
      },
    });

    expect(response.ok()).toBe(true);
    expect(response.headers()["access-control-allow-origin"]).toBeUndefined();
  });
});
