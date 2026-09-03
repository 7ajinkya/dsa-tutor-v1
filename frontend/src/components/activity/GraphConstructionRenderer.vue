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
    <div class="node-list">
      <span
        v-for="node in activity.nodes ?? []"
        :key="node"
        class="node-chip"
      >{{ node }}</span>
    </div>
    <label
      class="field-label"
      for="graph-edges"
    >Edges</label>
    <textarea
      id="graph-edges"
      v-model="answer"
      name="answer"
      rows="5"
      placeholder="One edge per line, for example A-B"
      :disabled="busy"
    />
  </ActivityFrame>
</template>
