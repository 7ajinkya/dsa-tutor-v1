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
    <pre
      v-if="activity.code"
      class="code-block"
    ><code>{{ activity.code }}</code></pre>
    <textarea
      v-model="answer"
      name="answer"
      rows="4"
      placeholder="Enter one output line per row."
      :disabled="busy"
    />
  </ActivityFrame>
</template>
