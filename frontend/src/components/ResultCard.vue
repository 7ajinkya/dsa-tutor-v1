<script setup lang="ts">
import type { Result } from "../api/types";

defineProps<{ result: Result }>();
</script>

<template>
  <article
    class="result-card"
    aria-live="polite"
  >
    <p class="eyebrow">
      Submitted result
    </p>
    <h2>{{ result.correct === true ? "Correct" : result.correct === false ? "Not quite" : "Response recorded" }}</h2>
    <p>{{ result.feedback }}</p>
    <dl class="result-facts">
      <div v-if="result.score !== null">
        <dt>Score</dt><dd>{{ result.score }}</dd>
      </div>
      <div v-if="result.confidence_signal">
        <dt>Confidence signal</dt><dd>{{ result.confidence_signal }}</dd>
      </div>
      <div v-if="result.answered_by">
        <dt>Answered by</dt><dd>{{ result.answered_by }}</dd>
      </div>
      <div v-if="result.assisted !== null">
        <dt>Assistance</dt><dd>{{ result.assisted ? "Assisted" : "Independent" }}</dd>
      </div>
    </dl>
    <p class="next-turn-note">
      The turn shown below is the next authoritative server turn.
    </p>
  </article>
</template>
