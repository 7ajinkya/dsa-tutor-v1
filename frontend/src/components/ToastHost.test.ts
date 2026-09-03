// @vitest-environment happy-dom
import { beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import ToastHost from "./ToastHost.vue";
import { useUiStore } from "../stores/ui";

function mountHost() {
  setActivePinia(createPinia());
  return mount(ToastHost, { global: { plugins: [] } });
}

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("C8 ToastHost (learner-facing recovery notices)", () => {
  it("renders nothing when there are no toasts", () => {
    const wrapper = mountHost();
    expect(wrapper.findAll(".toast")).toHaveLength(0);
  });

  it("renders the stale-recovery notice as an informational toast", async () => {
    const wrapper = mountHost();
    const ui = useUiStore();
    ui.markStaleAdopted();
    ui.pushToast("info", "Skipped ahead - showing the current task.");
    await nextTick();
    const toasts = wrapper.findAll(".toast");
    expect(toasts.length).toBe(1);
    expect(toasts[0].text()).toContain("Skipped ahead");
    expect(toasts[0].classes()).toContain("toast-info");
  });

  it("dismisses a toast from its dismiss button", async () => {
    const wrapper = mountHost();
    const ui = useUiStore();
    ui.pushToast("warning", "Temporary issue - your answer is kept.");
    await nextTick();
    expect(wrapper.findAll(".toast")).toHaveLength(1);
    await wrapper.find(".toast-dismiss").trigger("click");
    expect(wrapper.findAll(".toast")).toHaveLength(0);
  });
});
