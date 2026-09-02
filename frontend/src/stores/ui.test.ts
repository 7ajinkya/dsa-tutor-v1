import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useUiStore } from "./ui";

beforeEach(() => {
  setActivePinia(createPinia());
});

describe("useUiStore", () => {
  it("pushes and dismisses toasts with a cap", () => {
    const ui = useUiStore();
    for (let i = 0; i < 7; i++) ui.pushToast("info", `toast ${i}`);
    expect(ui.toasts.length).toBe(5);                       // capped
    ui.dismissToast(ui.toasts[0].id);
    expect(ui.toasts.length).toBe(4);
    ui.clearToasts();
    expect(ui.toasts.length).toBe(0);
  });

  it("tracks the stale-adopted flag", () => {
    const ui = useUiStore();
    expect(ui.staleAdopted).toBe(false);
    ui.markStaleAdopted();
    expect(ui.staleAdopted).toBe(true);
    ui.clearStaleAdopted();
    expect(ui.staleAdopted).toBe(false);
  });

  it("askConfirm resolves true when confirmed", async () => {
    const ui = useUiStore();
    const promise = ui.askConfirm({ title: "Reveal", message: "Counts as assisted." });
    expect(ui.confirmDialog?.title).toBe("Reveal");
    ui.resolveConfirm(true);
    await expect(promise).resolves.toBe(true);
    expect(ui.confirmDialog).toBeNull();
  });

  it("askConfirm resolves false when rejected", async () => {
    const ui = useUiStore();
    const promise = ui.askConfirm({ title: "Reveal", message: "Counts as assisted." });
    ui.resolveConfirm(false);
    await expect(promise).resolves.toBe(false);
  });
});
