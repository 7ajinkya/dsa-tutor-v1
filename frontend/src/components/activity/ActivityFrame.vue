<script setup lang="ts">
import { ref } from "vue";
import type { Activity } from "../../api/types";
import ExplainPanel from "../ExplainPanel.vue";
import HintDrawer from "../HintDrawer.vue";
import RevealDialog from "../RevealDialog.vue";

defineProps<{ activity: Activity; busy: boolean; error: string | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();

const revealDialogRef = ref<InstanceType<typeof RevealDialog> | null>(null);

function onRevealCta(): void {
  void revealDialogRef.value?.triggerReveal();
}
</script>

<template>
  <article
    class="activity-card"
    :aria-busy="busy ? 'true' : undefined"
  >
    <div class="activity-meta">
      <span class="activity-mode">{{ activity.mode }}</span>
      <span
        v-if="activity.generated"
        class="generated-badge"
      >Generated extra practice</span>
      <span
        v-if="activity.position"
        class="activity-position"
      >{{ activity.position.index }} / {{ activity.position.of }}</span>
    </div>
    <p class="activity-purpose">
      {{ activity.purpose }}
    </p>
    <h2>{{ activity.prompt }}</h2>

    <ExplainPanel
      :activity="activity"
      :busy="busy"
    />

    <form @submit.prevent="emit('submit', '')">
      <slot />
      <p
        v-if="error"
        class="activity-error"
        role="alert"
      >
        {{ error }}
      </p>
      <div
        v-else
        aria-live="polite"
      />
      <div class="activity-actions">
        <button
          v-if="activity.available_actions.includes('answer')"
          type="submit"
          class="primary-button submit-btn"
          :disabled="busy"
        >
          {{ busy ? "Submitting…" : "Submit answer" }}
        </button>
        <RevealDialog
          ref="revealDialogRef"
          :activity="activity"
          :busy="busy"
        />
        <HintDrawer
          :activity="activity"
          :busy="busy"
          @reveal="onRevealCta"
        />
      </div>
    </form>
  </article>
</template>
