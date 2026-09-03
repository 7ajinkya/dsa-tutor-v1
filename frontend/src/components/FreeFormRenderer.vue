<script setup lang="ts">
import { ref } from "vue";
import type { Activity } from "../api/types";
import ActivityFrame from "./activity/ActivityFrame.vue";

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
    <textarea
      v-model="answer"
      name="answer"
      rows="5"
      placeholder="Explain your reasoning in your own words."
      :disabled="busy"
    />
  </ActivityFrame>
</template>
