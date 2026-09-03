<script setup lang="ts">
import type { Theory } from "../api/types";
import { theoryScope } from "../views/sessionView";

defineProps<{ theory: Theory; busy: boolean }>();
const emit = defineEmits<{ acknowledge: [] }>();
</script>

<template>
  <article class="theory-panel">
    <p class="eyebrow">
      What do I do now?
    </p>
    <h2>{{ theory.unit.title }}</h2>
    <p class="theory-purpose">
      Study this server-provided explanation before continuing.
    </p>
    <div class="theory-copy">
      {{ theory.text }}
    </div>
    <div class="theory-next">
      <strong>What happens next?</strong>
      <span>{{ theoryScope(theory) }}.</span>
    </div>
    <button
      type="button"
      :disabled="busy"
      @click="emit('acknowledge')"
    >
      {{ busy ? "Recording…" : "I’ve read this — continue" }}
    </button>
  </article>
</template>
