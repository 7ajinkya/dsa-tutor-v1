/**
 * useUiStore (design §6): transient UI state — toasts, stale-adopted flag and
 * confirmation-dialog state. No session/learner data lives here.
 */
import { ref } from "vue";
import { defineStore } from "pinia";

export type ToastKind = "info" | "success" | "warning" | "error";

export interface Toast {
  id: number;
  kind: ToastKind;
  text: string;
}

export interface ConfirmDialog {
  id: number;
  title: string;
  message: string;
  confirmLabel: string;
  rejectLabel: string;
}

let toastSeq = 0;
let confirmSeq = 0;
const confirmResolvers = new Map<number, (accepted: boolean) => void>();

export const useUiStore = defineStore("ui", () => {
  const toasts = ref<Toast[]>([]);
  /** Set when the client adopted an authoritative `error.turn` after 409
   *  STALE_ACTIVITY (design §16); cleared on the next successful load. */
  const staleAdopted = ref(false);
  const confirmDialog = ref<ConfirmDialog | null>(null);

  function pushToast(kind: ToastKind, text: string): number {
    const id = ++toastSeq;
    toasts.value.push({ id, kind, text });
    if (toasts.value.length > 5) toasts.value.splice(0, toasts.value.length - 5);
    return id;
  }

  function dismissToast(id: number): void {
    toasts.value = toasts.value.filter((t) => t.id !== id);
  }

  function clearToasts(): void {
    toasts.value = [];
  }

  function markStaleAdopted(): void {
    staleAdopted.value = true;
  }

  function clearStaleAdopted(): void {
    staleAdopted.value = false;
  }

  /** Opens the confirmation dialog and resolves with the learner's choice. */
  function askConfirm(options: { title: string; message: string;
                                 confirmLabel?: string; rejectLabel?: string }): Promise<boolean> {
    const id = ++confirmSeq;
    confirmDialog.value = {
      id,
      title: options.title,
      message: options.message,
      confirmLabel: options.confirmLabel ?? "Confirm",
      rejectLabel: options.rejectLabel ?? "Cancel",
    };
    return new Promise((resolve) => {
      confirmResolvers.set(id, resolve);
    });
  }

  function resolveConfirm(accepted: boolean): void {
    const dialog = confirmDialog.value;
    if (dialog === null) return;
    confirmDialog.value = null;
    const resolve = confirmResolvers.get(dialog.id);
    confirmResolvers.delete(dialog.id);
    resolve?.(accepted);
  }

  return {
    toasts, staleAdopted, confirmDialog,
    pushToast, dismissToast, clearToasts,
    markStaleAdopted, clearStaleAdopted, askConfirm, resolveConfirm,
  };
});
