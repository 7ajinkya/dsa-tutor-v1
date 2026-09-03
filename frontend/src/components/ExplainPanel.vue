<script setup lang="ts">
import { computed, hasInjectionContext, inject, ref, watch } from "vue";
import { piniaSymbol } from "pinia";
import type { Activity } from "../api/types";
import { useSessionStore } from "../stores/session";

const props = defineProps<{
  activity: Activity;
  busy?: boolean;
}>();

const hasPinia = hasInjectionContext() && inject(piniaSymbol, null) !== null;
const sessionStore = hasPinia ? useSessionStore() : null;




const isExplaining = ref(false);
const explainError = ref<string | null>(null);
const userDismissed = ref(false);

const canExplain = computed(() =>
  props.activity.available_actions?.includes("explain") ?? false
);

const lastExplanation = computed(() => sessionStore?.lastExplanation ?? null);

const isExplanationVisible = computed(() =>
  Boolean(lastExplanation.value) && !userDismissed.value
);

async function fetchExplanation(): Promise<void> {
  if (!sessionStore || isExplaining.value || props.busy || sessionStore.inFlight) return;
  explainError.value = null;
  userDismissed.value = false;
  isExplaining.value = true;
  try {
    await sessionStore.explainCurrent();
  } catch (err: unknown) {
    explainError.value = err instanceof Error ? err.message : "Failed to retrieve explanation.";
  } finally {
    isExplaining.value = false;
  }
}

function dismissExplanation(): void {
  userDismissed.value = true;
}

watch(() => props.activity.id, () => {
  explainError.value = null;
  userDismissed.value = false;
});

defineExpose({
  fetchExplanation,
  dismissExplanation,
  isExplaining,
  isExplanationVisible,
});
</script>


<template>
  <div
    v-if="canExplain || isExplanationVisible"
    class="explain-container"
  >
    <!-- Trigger Button -->
    <button
      v-if="canExplain && !isExplanationVisible"
      type="button"
      class="explain-trigger-btn secondary-button"
      :disabled="busy || isExplaining || sessionStore?.inFlight"
      @click="fetchExplanation"
    >
      {{ isExplaining ? "Explaining…" : "Explain this task" }}
    </button>

    <!-- Inline Explanation Display below prompt -->
    <div
      v-if="isExplanationVisible"
      class="explain-panel"
      role="region"
      aria-label="Explanation"
    >
      <div class="explain-panel-header">
        <h4>Why this task?</h4>
        <button
          type="button"
          class="explain-close-btn"
          aria-label="Close explanation"
          @click="dismissExplanation"
        >
          Close
        </button>
      </div>
      <p class="explain-body">
        {{ lastExplanation }}
      </p>
    </div>

    <p
      v-if="explainError"
      class="explain-error-message"
      role="alert"
    >
      {{ explainError }}
    </p>
  </div>
</template>
