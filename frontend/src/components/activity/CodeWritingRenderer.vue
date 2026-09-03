<script setup lang="ts">
import { ref } from "vue";
import type { Activity } from "../../api/types";
import ActivityFrame from "./ActivityFrame.vue";

const props = defineProps<{ activity: Activity; busy: boolean; error: string | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();
const answer = ref(props.activity.starter ?? "");
</script>

<template>
  <ActivityFrame
    :activity="activity"
    :busy="busy"
    :error="error"
    @submit="emit('submit', answer)"
  >
    <p
      v-if="activity.function_name"
      class="field-label"
    >
      Function: <code>{{ activity.function_name }}</code>
    </p>
    <textarea
      v-model="answer"
      name="answer"
      rows="10"
      class="code-editor"
      :placeholder="activity.starter ?? 'Write your code here.'"
      :disabled="busy"
    />
  </ActivityFrame>
</template>
