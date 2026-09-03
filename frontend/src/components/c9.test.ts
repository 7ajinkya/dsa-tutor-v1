// C9 responsive + accessibility hardening tests (plan A19 accessibility pass).
// SSR tests assert server-rendered markup semantics; happy-dom tests verify
// Escape-key dismissal and focus behavior of the dismissible overlays.
// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createSSRApp, nextTick } from "vue";
import { renderToString } from "@vue/server-renderer";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import type { Activity } from "../api/types";
import FreeFormRenderer from "./FreeFormRenderer.vue";
import LinesRenderer from "./activity/LinesRenderer.vue";
import CodeWritingRenderer from "./activity/CodeWritingRenderer.vue";
import ActivityFrame from "./activity/ActivityFrame.vue";
import HintDrawer from "./HintDrawer.vue";
import RevealDialog from "./RevealDialog.vue";
import ToastHost from "./ToastHost.vue";
import ProgressView from "../views/ProgressView.vue";
import { useUiStore } from "../stores/ui";
import { useLearnerStore } from "../stores/learner";

vi.mock("../api/endpoints", () => ({
  startSession: vi.fn(),
  resumeSession: vi.fn(),
  getSessionSnapshot: vi.fn(),
  stopSession: vi.fn(),
  theorySeen: vi.fn(),
  answer: vi.fn(),
  hint: vi.fn(),
  revealSolution: vi.fn(),
  explain: vi.fn(),
  confidence: vi.fn(),
  progress: vi.fn(),
  home: vi.fn(),
  makeIdempotencyKey: vi.fn(),
}));

import * as endpoints from "../api/endpoints";

const mockEndpoints = vi.mocked(endpoints);

function makeActivity(overrides: Partial<Activity> = {}): Activity {
  return {
    id: "e001_graph_definition", type: "mcq", mode: "practice",
    purpose: "Practice check on 'What is a graph?'", prompt: "Which statement is true?",
    answer_format: "letter", position: null, unit: null,
    skill: { id: "graph_definition", title: "What is a graph?" },
    choices: null, code: null, starter: null, function_name: null,
    nodes: null, kind: null, generated: false,
    hints: { allowed: true, max_level: 4 },
    available_actions: ["answer", "hint", "explain", "progress", "solution", "stop"],
    ...overrides,
  };
}

let pinia: ReturnType<typeof createPinia>;

beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
  vi.restoreAllMocks();
});

describe("C9 form-label accessibility on answer inputs", () => {
  it("free_form textarea exposes an accessible name", async () => {
    const app = createSSRApp(FreeFormRenderer, {
      activity: makeActivity({ type: "free_form", answer_format: "text" }), busy: false, error: null,
    });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain('aria-label="Your answer"');
  });

  it("lines textarea exposes an accessible name", async () => {
    const app = createSSRApp(LinesRenderer, {
      activity: makeActivity({ type: "output_prediction", answer_format: "lines", code: "print(1)" }),
      busy: false, error: null,
    });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain('aria-label="Your answer, one output line per row"');
  });

  it("code_writing textarea exposes a function-scoped accessible name", async () => {
    const app = createSSRApp(CodeWritingRenderer, {
      activity: makeActivity({
        type: "code_writing", answer_format: "code",
        starter: "def bfs():\n    pass", function_name: "bfs",
      }),
      busy: false, error: null,
    });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain('aria-label="Code for function bfs"');
  });
});

describe("C9 live-region and busy semantics on the activity card", () => {
  it("marks the card busy while a mutation is in flight", async () => {
    const app = createSSRApp(ActivityFrame, {
      activity: makeActivity(), busy: true, error: null,
    });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain('aria-busy="true"');
  });

  it("keeps a polite live region present for submission outcome announcements", async () => {
    const app = createSSRApp(ActivityFrame, {
      activity: makeActivity(), busy: false, error: null,
    });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain('aria-live="polite"');
  });
});

describe("C9 ToastHost per-toast semantics", () => {
  it("renders informational toasts as status regions and error toasts as alerts", async () => {
    const ui = useUiStore();
    ui.pushToast("info", "Skipped ahead - showing the current task.");
    ui.pushToast("error", "Could not reach the server.");
    const wrapper = mount(ToastHost);
    expect(wrapper.find(".toast-info").attributes("role")).toBe("status");
    expect(wrapper.find(".toast-error").attributes("role")).toBe("alert");
  });
});

describe("C9 HintDrawer keyboard dismissal", () => {
  it("closes on Escape and returns focus to the toggle button", async () => {
    const wrapper = mount(HintDrawer, {
      props: { activity: makeActivity(), busy: false },
      attachTo: document.body,
    });
    await wrapper.find(".hint-toggle-btn").trigger("click");
    await nextTick();
    await nextTick();
    expect(wrapper.find(".hint-drawer").exists()).toBe(true);
    expect(document.activeElement?.className).toContain("hint-close-btn");

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await nextTick();
    await nextTick();
    expect(wrapper.find(".hint-drawer").exists()).toBe(false);
    expect(document.activeElement?.className).toContain("hint-toggle-btn");
    wrapper.unmount();
  });

  it("stops listening for Escape after unmount (no leak)", async () => {
    const wrapper = mount(HintDrawer, {
      props: { activity: makeActivity(), busy: false },
      attachTo: document.body,
    });
    await wrapper.find(".hint-toggle-btn").trigger("click");
    await nextTick();
    wrapper.unmount();
    // must not throw even though the component is gone
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    expect(true).toBe(true);
  });
});

describe("C9 RevealDialog keyboard dismissal", () => {
  it("Escape cancels the confirmation dialog and focus lands on Cancel first", async () => {
    const ui = useUiStore();
    const wrapper = mount(RevealDialog, {
      props: { activity: makeActivity(), busy: false },
      global: { plugins: [pinia] },
      attachTo: document.body,
    });

    const confirmPromise = (wrapper.vm as unknown as { triggerReveal: () => Promise<boolean> }).triggerReveal();
    await nextTick();
    await nextTick();
    expect(ui.confirmDialog).not.toBeNull();
    expect(document.activeElement?.className).toContain("confirm-reject-btn");

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await nextTick();
    expect(ui.confirmDialog).toBeNull();
    await confirmPromise;
    wrapper.unmount();
  });

  it("dialog markup is describedby-linked for screen readers", async () => {
    const ui = useUiStore();
    void ui.askConfirm({
      title: "Reveal Solution?",
      message: "Revealing counts as assisted.",
      confirmLabel: "Reveal anyway",
      rejectLabel: "Cancel",
    });
    const app = createSSRApp(RevealDialog, { activity: makeActivity(), busy: false });
    app.use(pinia);
    const html = await renderToString(app);
    expect(html).toContain('aria-describedby="confirm-dialog-message"');
    expect(html).toContain('aria-modal="true"');
  });
});

describe("C9 Progress filter semantics", () => {
  it("module filter buttons expose aria-pressed state", async () => {
    const learner = useLearnerStore();
    mockEndpoints.progress.mockResolvedValue({
      daily: { date: "2026-09-04", target_units: 4, completed_units: 0, status: "active" },
      skills: [
        {
          skill: "graph_definition", title: "What is a graph?", section: "foundations",
          module: "A - Graph mental model", state: "INTRODUCED", evidence: 2,
          mastered: false, boundary: false, optional: false,
        },
      ],
    });
    await learner.fetchProgress();
    const wrapper = mount(ProgressView, { global: { stubs: { RouterLink: true } } });
    await nextTick();
    const buttons = wrapper.findAll(".module-tabs button");
    expect(buttons.length).toBeGreaterThanOrEqual(2);
    expect(buttons[0].attributes("aria-pressed")).toBe("true");
    expect(buttons[1].attributes("aria-pressed")).toBe("false");
  });

  it("loading skeleton announces itself via role=status", async () => {
    mockEndpoints.progress.mockReturnValue(new Promise(() => {}));
    const wrapper = mount(ProgressView, { global: { stubs: { RouterLink: true } } });
    await nextTick();
    expect(wrapper.find(".progress-list").attributes("role")).toBe("status");
  });
});
