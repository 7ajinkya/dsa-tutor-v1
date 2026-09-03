<script setup lang="ts">
import { computed, hasInjectionContext, inject, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { piniaSymbol } from "pinia";
import type { Activity } from "../api/types";
import { useSessionStore } from "../stores/session";
import { useUiStore } from "../stores/ui";

const props = defineProps<{
  activity: Activity;
  busy?: boolean;
}>();

const hasPinia = hasInjectionContext() && inject(piniaSymbol, null) !== null;
const sessionStore = hasPinia ? useSessionStore() : null;
const uiStore = hasPinia ? useUiStore() : null;


const isRevealing = ref(false);
const revealError = ref<string | null>(null);

const canReveal = computed(() =>
  props.activity.available_actions?.includes("solution") ?? false
);

const lastSolution = computed(() => sessionStore?.lastSolution ?? null);

async function triggerReveal(): Promise<void> {
  if (!sessionStore || !uiStore || isRevealing.value || props.busy || sessionStore.inFlight) return;
  revealError.value = null;

  const confirmed = await uiStore.askConfirm({
    title: "Reveal Solution?",
    message: "Revealing the solution counts as assisted and does not earn independent evidence for this task.",
    confirmLabel: "Reveal anyway",
    rejectLabel: "Cancel",
  });

  if (!confirmed) return;

  isRevealing.value = true;
  try {
    await sessionStore.revealSolution();
  } catch (err: unknown) {
    revealError.value = err instanceof Error ? err.message : "Failed to reveal solution.";
  } finally {
    isRevealing.value = false;
  }
}

watch(() => props.activity.id, () => {
  revealError.value = null;
});

/** C9: Escape cancels the open confirmation dialog (no keyboard trap). */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && uiStore?.confirmDialog) {
    event.stopPropagation();
    uiStore.resolveConfirm(false);
  }
}

watch(() => uiStore?.confirmDialog ?? null, async (dialog) => {
  if (dialog !== null) {
    window.addEventListener("keydown", onKeydown);
    await nextTick();
    document.querySelector<HTMLElement>(".confirm-reject-btn")?.focus();
  } else {
    window.removeEventListener("keydown", onKeydown);
    await nextTick();
    document.querySelector<HTMLElement>(".reveal-trigger-btn")?.focus();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
});

defineExpose({
  triggerReveal,
});
</script>

<template>
  <div class="reveal-container">
    <!-- Trigger button if available in actions and not already revealed -->
    <button
      v-if="canReveal && !lastSolution"
      type="button"
      class="reveal-trigger-btn secondary-button"
      :disabled="busy || isRevealing || sessionStore?.inFlight"
      @click="triggerReveal"
    >
      {{ isRevealing ? "Revealing…" : "Reveal solution" }}
    </button>

    <!-- Confirmation Modal Dialog -->
    <div
      v-if="uiStore?.confirmDialog"
      class="confirm-modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby="confirm-dialog-message"
    >
      <div class="confirm-modal-card">
        <h3 id="confirm-dialog-title">
          {{ uiStore.confirmDialog.title }}
        </h3>
        <p
          id="confirm-dialog-message"
          class="confirm-modal-message"
        >
          {{ uiStore.confirmDialog.message }}
        </p>
        <div class="confirm-modal-actions">
          <button
            type="button"
            class="danger-button confirm-accept-btn"
            :disabled="isRevealing"
            @click="uiStore.resolveConfirm(true)"
          >
            {{ uiStore.confirmDialog.confirmLabel }}
          </button>
          <button
            type="button"
            class="secondary-button confirm-reject-btn"
            :disabled="isRevealing"
            @click="uiStore.resolveConfirm(false)"
          >
            {{ uiStore.confirmDialog.rejectLabel }}
          </button>
        </div>
      </div>
    </div>

    <!-- Revealed Solution Inset -->
    <div
      v-if="lastSolution"
      class="solution-inset"
      role="region"
      aria-label="Revealed solution"
    >
      <div class="solution-header">
        <h4>Revealed solution</h4>
        <span class="assisted-badge">Assisted attempt</span>
      </div>
      <pre class="solution-content">{{ lastSolution }}</pre>
      <p class="solution-warning">
        Revealing counts as assisted and does not earn independent evidence. Resubmissions or follow-up answers will be recorded as assisted.
      </p>
    </div>

    <p
      v-if="revealError"
      class="reveal-error-message"
      role="alert"
    >
      {{ revealError }}
    </p>
  </div>
</template>
