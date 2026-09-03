<script setup lang="ts">
import { ref } from "vue";
import type { Activity } from "../../api/types";
import ActivityFrame from "./ActivityFrame.vue";

defineProps<{ activity: Activity; busy: boolean; error: string | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();
const answer = ref("");
</script>

<template>
  <ActivityFrame
    :activity="activity"
    :busy="busy"
    :error="error"
    @submit="emit('submit', answer)"
  >
    <label
      class="field-label"
      for="complexity-answer"
    >Big-O answer<span v-if="activity.kind"> ({{ activity.kind }})</span></label>
    <input
      id="complexity-answer"
      v-model="answer"
      name="answer"
      type="text"
      placeholder="e.g. O(V + E)"
      :disabled="busy"
    >
  </ActivityFrame>
</template>
