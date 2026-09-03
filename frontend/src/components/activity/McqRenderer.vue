<script setup lang="ts">
import { ref } from "vue";
import type { Activity } from "../../api/types";
import ActivityFrame from "./ActivityFrame.vue";

defineProps<{ activity: Activity; busy: boolean; error: string | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();
const selected = ref("");
</script>

<template>
  <ActivityFrame
    :activity="activity"
    :busy="busy"
    :error="error"
    @submit="emit('submit', selected)"
  >
    <fieldset class="choice-list">
      <legend class="sr-only">
        Choose an answer
      </legend>
      <label
        v-for="choice in activity.choices ?? []"
        :key="choice.id"
      >
        <input
          v-model="selected"
          type="radio"
          name="answer"
          :value="choice.id"
          :disabled="busy"
        >
        <span>{{ choice.text }}</span>
      </label>
    </fieldset>
  </ActivityFrame>
</template>
