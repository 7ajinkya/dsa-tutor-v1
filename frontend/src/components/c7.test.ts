import { createSSRApp } from "vue";
import { renderToString } from "@vue/server-renderer";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import type { Activity, SessionInfo, TurnEnvelope } from "../api/types";
import { useSessionStore } from "../stores/session";
import { useUiStore } from "../stores/ui";
import ExplainPanel from "./ExplainPanel.vue";
import HintDrawer from "./HintDrawer.vue";
import RevealDialog from "./RevealDialog.vue";
import ActivityFrame from "./activity/ActivityFrame.vue";

interface ComponentWithSetup {
  setup: (
    props: Record<string, unknown>,
    ctx: {
      expose: (obj: Record<string, unknown>) => void;
      emit: (event: string, ...args: unknown[]) => void;
    },
  ) => unknown;
}

interface HintDrawerExposed {
  requestNextHint: () => Promise<void>;
  onRevealCta: () => void;
  isExhausted: { value: boolean };
}

interface RevealDialogExposed {
  triggerReveal: () => Promise<void>;
}

interface ExplainPanelExposed {
  fetchExplanation: () => Promise<void>;
  dismissExplanation: () => void;
  isExplanationVisible: { value: boolean };
}


const sampleSession: SessionInfo = {
  id: 42,
  status: "active",
  pace: "normal",
  budget_minutes: 25,
  remaining_minutes: 20,
  started_at: null,
  ended_at: null,
  end_reason_code: null,
  end_reason_detail: null,
  daily: null,
};

function makeActivity(overrides: Partial<Activity> = {}): Activity {
  return {
    id: "act-01",
    type: "mcq",
    mode: "practice",
    purpose: "Practice check",
    prompt: "What is the degree of vertex A?",
    answer_format: "letter",
    position: { index: 1, of: 3 },
    unit: null,
    skill: { id: "graphs", title: "Graphs" },
    choices: [{ id: "a", text: "Choice A" }],
    code: null,
    starter: null,
    function_name: null,
    nodes: null,
    kind: null,
    generated: false,
    hints: { allowed: true, max_level: 3 },
    available_actions: ["answer", "hint", "explain", "solution"],
    ...overrides,
  };
}

function makeTurn(activity: Activity, overrides: Partial<TurnEnvelope> = {}): TurnEnvelope {
  return {
    type: "activity",
    session: sampleSession,
    step: null,
    notice: null,
    activity,
    theory: null,
    result: null,
    hint: null,
    ...overrides,
  };
}

describe("C7: HintDrawer.vue", () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("renders when available_actions includes 'hint'", async () => {
    const activity = makeActivity({ available_actions: ["hint"] });
    const app = createSSRApp(HintDrawer, { activity, busy: false });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain("Hint");
    expect(html).toContain("hint-toggle-btn");
  });

  it("is hidden when available_actions does not include 'hint'", async () => {
    const activity = makeActivity({ available_actions: ["answer", "explain"] });
    const app = createSSRApp(HintDrawer, { activity, busy: false });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).not.toContain("hint-toggle-btn");
    expect(html).toBe("<!---->");
  });

  it("does not infer hint availability from activity type", async () => {
    // MCQ type without 'hint' action -> must NOT render
    const mcqNoHint = makeActivity({ type: "mcq", available_actions: ["answer"] });
    const app1 = createSSRApp(HintDrawer, { activity: mcqNoHint, busy: false });
    app1.use(pinia);
    const html1 = await renderToString(app1);
    expect(html1).toBe("<!---->");

    // Code writing type with 'hint' action -> MUST render

    const codeWithHint = makeActivity({ type: "code_writing", available_actions: ["hint"] });
    const app2 = createSSRApp(HintDrawer, { activity: codeWithHint, busy: false });
    app2.use(pinia);
    const html2 = await renderToString(app2);
    expect(html2).toContain("hint-toggle-btn");
  });

  it("shows disabled state when busy", async () => {
    const activity = makeActivity({ available_actions: ["hint"] });
    const app = createSSRApp(HintDrawer, { activity, busy: true });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain("disabled");
  });

  it("renders server-provided turn.hint level/kind/text", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["hint"] });
    sessionStore.session = sampleSession;
    sessionStore.turn = makeTurn(activity, {
      hint: { level: 1, kind: "socratic", text: "Look at the incident edges." },
    });

    const app = createSSRApp(HintDrawer, { activity, busy: false });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain("Hint 1/3");
  });

  it("renders level progression when turn.hint updates", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["hint"] });
    sessionStore.session = sampleSession;

    // First hint level
    sessionStore.turn = makeTurn(activity, {
      hint: { level: 1, kind: "socratic", text: "First hint." },
    });
    const app1 = createSSRApp(HintDrawer, { activity, busy: false });
    app1.use(pinia);
    const html1 = await renderToString(app1);
    expect(html1).toContain("Hint 1/3");

    // Next hint level
    sessionStore.turn = makeTurn(activity, {
      hint: { level: 2, kind: "nudge", text: "Second hint." },
    });
    const app2 = createSSRApp(HintDrawer, { activity, busy: false });
    app2.use(pinia);
    const html2 = await renderToString(app2);
    expect(html2).toContain("Hint 2/3");
  });

  it("executes requestNextHint and delegates to sessionStore.requestHint()", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["hint"] });
    sessionStore.session = sampleSession;
    sessionStore.turn = makeTurn(activity);

    let requested = false;
    sessionStore.requestHint = async () => {
      requested = true;
      sessionStore.turn = makeTurn(activity, {
        hint: { level: 1, kind: "socratic", text: "Look closely at edges." },
      });
    };

    let drawerExposed: HintDrawerExposed | undefined;
    const app = createSSRApp({
      setup() {
        const exposed: Record<string, unknown> = {};
        (HintDrawer as unknown as ComponentWithSetup).setup(
          { activity, busy: false },
          { expose: (obj: Record<string, unknown>) => Object.assign(exposed, obj), emit: () => {} },
        );
        drawerExposed = exposed as unknown as HintDrawerExposed;
        return () => null;
      },
    });
    app.use(pinia);
    await renderToString(app);

    await drawerExposed!.requestNextHint();
    expect(requested).toBe(true);
    expect(sessionStore.turn?.hint?.level).toBe(1);
  });

  it("sets exhausted state and emits reveal when LADDER_EXHAUSTED occurs", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["hint"] });
    sessionStore.session = sampleSession;
    sessionStore.turn = makeTurn(activity);

    const { ApiClientError } = await import("../api/client");
    sessionStore.requestHint = async () => {
      throw new ApiClientError(409, "LADDER_EXHAUSTED", "Hints exhausted", false);
    };

    let emittedReveal = false;
    let drawerExposed: HintDrawerExposed | undefined;
    const app = createSSRApp({
      setup() {
        const exposed: Record<string, unknown> = {};
        (HintDrawer as unknown as ComponentWithSetup).setup(
          { activity, busy: false },
          {
            expose: (obj: Record<string, unknown>) => Object.assign(exposed, obj),
            emit: (evt: string) => { if (evt === "reveal") emittedReveal = true; },
          },
        );
        drawerExposed = exposed as unknown as HintDrawerExposed;
        return () => null;
      },
    });
    app.use(pinia);
    await renderToString(app);

    await drawerExposed!.requestNextHint();
    expect(drawerExposed!.isExhausted.value).toBe(true);

    drawerExposed!.onRevealCta();
    expect(emittedReveal).toBe(true);
  });
});



describe("C7: RevealDialog.vue", () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("renders reveal trigger when available_actions includes 'solution'", async () => {
    const actSolution = makeActivity({ available_actions: ["solution"] });
    const app1 = createSSRApp(RevealDialog, { activity: actSolution, busy: false });
    app1.use(pinia);
    expect(await renderToString(app1)).toContain("Reveal solution");

    const actReveal = makeActivity({ available_actions: ["reveal"] });
    const app = createSSRApp(RevealDialog, { activity: actReveal, busy: false });
    app.use(pinia);
    expect(await renderToString(app)).not.toContain("Reveal solution");
  });

  it("is hidden when available_actions does not include reveal/solution", async () => {
    const activity = makeActivity({ available_actions: ["answer", "hint"] });
    const app = createSSRApp(RevealDialog, { activity, busy: false });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).not.toContain("Reveal solution");
  });

  it("shows disabled state when busy", async () => {
    const activity = makeActivity({ available_actions: ["solution"] });
    const app = createSSRApp(RevealDialog, { activity, busy: true });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain("disabled");
  });

  it("renders confirmation warning dialog when askConfirm is invoked", async () => {
    const uiStore = useUiStore();
    const activity = makeActivity({ available_actions: ["solution"] });

    // Initiate confirmation dialog
    void uiStore.askConfirm({
      title: "Reveal Solution?",
      message: "Revealing the solution counts as assisted and does not earn independent evidence for this task.",
      confirmLabel: "Reveal anyway",
      rejectLabel: "Cancel",
    });

    const app = createSSRApp(RevealDialog, { activity, busy: false });
    app.use(pinia);
    const html = await renderToString(app);

    expect(html).toContain("Reveal Solution?");
    expect(html).toContain("Revealing the solution counts as assisted and does not earn independent evidence");
    expect(html).toContain("Reveal anyway");
    expect(html).toContain("Cancel");
  });

  it("displays sessionStore.lastSolution only after successful reveal", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["solution"] });

    // Initially, no solution
    const app1 = createSSRApp(RevealDialog, { activity, busy: false });
    app1.use(pinia);
    expect(await renderToString(app1)).not.toContain("solution-inset");

    // After reveal solution
    sessionStore.lastSolution = "The degree is 3 because vertex A connects to B, C, and D.";
    const app2 = createSSRApp(RevealDialog, { activity, busy: false });
    app2.use(pinia);
    const html2 = await renderToString(app2);

    expect(html2).toContain("solution-inset");
    expect(html2).toContain("Revealed solution");
    expect(html2).toContain("The degree is 3 because vertex A connects to B, C, and D.");
    expect(html2).toContain("Assisted attempt");
    // Trigger button is hidden once solution is revealed
    expect(html2).not.toContain("reveal-trigger-btn");
  });

  it("awaits confirmation before calling revealSolution: confirmed branch", async () => {
    const sessionStore = useSessionStore();
    const uiStore = useUiStore();
    const activity = makeActivity({ available_actions: ["solution"] });
    sessionStore.session = sampleSession;
    sessionStore.turn = makeTurn(activity);

    let revealCalled = false;
    sessionStore.revealSolution = async () => {
      revealCalled = true;
      sessionStore.lastSolution = "Solution 42";
    };

    let triggerRevealFn: (() => Promise<void>) | undefined;
    const app = createSSRApp({
      setup() {
        const exposed: Record<string, unknown> = {};
        (RevealDialog as unknown as ComponentWithSetup).setup(
          { activity, busy: false },
          { expose: (obj: Record<string, unknown>) => Object.assign(exposed, obj), emit: () => {} },
        );
        triggerRevealFn = (exposed as unknown as RevealDialogExposed).triggerReveal;
        return () => null;
      },
    });
    app.use(pinia);
    await renderToString(app);

    expect(typeof triggerRevealFn).toBe("function");
    const revealPromise = triggerRevealFn!();
    expect(uiStore.confirmDialog?.title).toBe("Reveal Solution?");
    expect(uiStore.confirmDialog?.message).toContain("Revealing the solution counts as assisted");

    uiStore.resolveConfirm(true);
    await revealPromise;
    expect(revealCalled).toBe(true);
    expect(sessionStore.lastSolution).toBe("Solution 42");
  });

  it("awaits confirmation before calling revealSolution: cancelled branch", async () => {
    const sessionStore = useSessionStore();
    const uiStore = useUiStore();
    const activity = makeActivity({ available_actions: ["solution"] });
    sessionStore.session = sampleSession;
    sessionStore.turn = makeTurn(activity);

    let revealCalled = false;
    sessionStore.revealSolution = async () => {
      revealCalled = true;
    };

    let triggerRevealFn: (() => Promise<void>) | undefined;
    const app = createSSRApp({
      setup() {
        const exposed: Record<string, unknown> = {};
        (RevealDialog as unknown as ComponentWithSetup).setup(
          { activity, busy: false },
          { expose: (obj: Record<string, unknown>) => Object.assign(exposed, obj), emit: () => {} },
        );
        triggerRevealFn = (exposed as unknown as RevealDialogExposed).triggerReveal;
        return () => null;
      },
    });
    app.use(pinia);
    await renderToString(app);

    expect(typeof triggerRevealFn).toBe("function");
    const revealPromise = triggerRevealFn!();
    expect(uiStore.confirmDialog).not.toBeNull();

    uiStore.resolveConfirm(false);
    await revealPromise;
    expect(revealCalled).toBe(false);
  });

});



describe("C7: ExplainPanel.vue", () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("shows trigger only when available_actions includes 'explain'", async () => {
    const actWithExplain = makeActivity({ available_actions: ["explain"] });
    const app1 = createSSRApp(ExplainPanel, { activity: actWithExplain, busy: false });
    app1.use(pinia);
    expect(await renderToString(app1)).toContain("Explain this task");

    const actWithoutExplain = makeActivity({ available_actions: ["answer", "hint"] });
    const app2 = createSSRApp(ExplainPanel, { activity: actWithoutExplain, busy: false });
    app2.use(pinia);
    expect(await renderToString(app2)).toBe("<!---->");
  });


  it("shows disabled state when busy", async () => {
    const activity = makeActivity({ available_actions: ["explain"] });
    const app = createSSRApp(ExplainPanel, { activity, busy: true });
    app.use(pinia);
    expect(await renderToString(app)).toContain("disabled");
  });

  it("displays lastExplanation inline when populated and is provider-neutral", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["explain"] });
    sessionStore.lastExplanation = "Graphs represent pairwise relations between objects.";

    const app = createSSRApp(ExplainPanel, { activity, busy: false });
    app.use(pinia);
    const html = await renderToString(app);

    expect(html).toContain("explain-panel");
    expect(html).toContain("Why this task?");
    expect(html).toContain("Graphs represent pairwise relations between objects.");
    // Provider-neutral
    expect(html).not.toContain("OpenAI");
    expect(html).not.toContain("GPT");
    expect(html).not.toContain("Claude");
    expect(html).not.toContain("Anthropic");
  });

  it("calls sessionStore.explainCurrent() on fetchExplanation and handles dismissal", async () => {
    const sessionStore = useSessionStore();
    const activity = makeActivity({ available_actions: ["explain"] });
    sessionStore.session = sampleSession;
    sessionStore.turn = makeTurn(activity);

    let explained = false;
    sessionStore.explainCurrent = async () => {
      explained = true;
      sessionStore.lastExplanation = "Graphs capture adjacency.";
    };

    let panelExposed: ExplainPanelExposed | undefined;
    const app = createSSRApp({
      setup() {
        const exposed: Record<string, unknown> = {};
        (ExplainPanel as unknown as ComponentWithSetup).setup(
          { activity, busy: false },
          { expose: (obj: Record<string, unknown>) => Object.assign(exposed, obj), emit: () => {} },
        );
        panelExposed = exposed as unknown as ExplainPanelExposed;
        return () => null;
      },
    });
    app.use(pinia);
    await renderToString(app);

    await panelExposed!.fetchExplanation();
    expect(explained).toBe(true);
    expect(panelExposed!.isExplanationVisible.value).toBe(true);

    panelExposed!.dismissExplanation();
    expect(panelExposed!.isExplanationVisible.value).toBe(false);
  });
});



describe("C7: ActivityFrame.vue integration", () => {
  let pinia: ReturnType<typeof createPinia>;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  it("renders all available controls when actions are permitted", async () => {
    const activity = makeActivity({
      available_actions: ["answer", "hint", "explain", "solution"],
    });

    const app = createSSRApp({
      components: { ActivityFrame },
      template: `<ActivityFrame :activity="activity" :busy="false" :error="null"><p>slot</p></ActivityFrame>`,
      setup() {
        return { activity };
      },
    });
    app.use(pinia);
    const html = await renderToString(app);

    expect(html).toContain("Submit answer");
    expect(html).toContain("Explain this task");
    expect(html).toContain("Reveal solution");
    expect(html).toContain("Hint");
  });

  it("omits hint, explain, and reveal when available_actions only has 'answer'", async () => {
    const activity = makeActivity({
      available_actions: ["answer"],
    });

    const app = createSSRApp({
      components: { ActivityFrame },
      template: `<ActivityFrame :activity="activity" :busy="false" :error="null"><p>slot</p></ActivityFrame>`,
      setup() {
        return { activity };
      },
    });
    app.use(pinia);
    const html = await renderToString(app);

    expect(html).toContain("Submit answer");
    expect(html).not.toContain("Explain this task");
    expect(html).not.toContain("Reveal solution");
    expect(html).not.toContain("hint-toggle-btn");
  });
});
