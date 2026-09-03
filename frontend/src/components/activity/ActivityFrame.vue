<script setup lang="ts">
import type { Activity } from "../../api/types";

defineProps<{ activity: Activity; busy: boolean; error: string | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();
</script>

<template>
  <article class="activity-card">
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
    <form @submit.prevent="emit('submit', '')">
      <slot />
      <p
        v-if="error"
        class="activity-error"
        role="alert"
      >
        {{ error }}
      </p>
      <button
        v-if="activity.available_actions.includes('answer')"
        type="submit"
        :disabled="busy"
      >
        {{ busy ? "Submitting…" : "Submit answer" }}
      </button>
    </form>
  </article>
</template>
