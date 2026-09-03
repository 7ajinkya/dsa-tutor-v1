<script setup lang="ts">
import { computed } from "vue";
import type { Activity } from "../../api/types";
import CodeWritingRenderer from "./CodeWritingRenderer.vue";
import ComplexityRenderer from "./ComplexityRenderer.vue";
import FreeFormRenderer from "../FreeFormRenderer.vue";
import GraphConstructionRenderer from "./GraphConstructionRenderer.vue";
import LinesRenderer from "./LinesRenderer.vue";
import McqRenderer from "./McqRenderer.vue";
import { rendererForType } from "./rendererContract";

const props = defineProps<{ activity: Activity; busy: boolean; error: string | null }>();
const emit = defineEmits<{ submit: [answer: string] }>();
const renderer = computed(() => rendererForType(props.activity.type));
const rendererComponents = {
  mcq: McqRenderer,
  free_form: FreeFormRenderer,
  lines: LinesRenderer,
  complexity_question: ComplexityRenderer,
  code_writing: CodeWritingRenderer,
  graph_construction: GraphConstructionRenderer,
};
</script>

<template>
  <component
    :is="rendererComponents[renderer]"
    v-if="renderer !== 'unknown'"
    :activity="activity"
    :busy="busy"
    :error="error"
    @submit="emit('submit', $event)"
  />
  <article
    v-else
    class="activity-card defensive-activity"
  >
    <div class="activity-meta">
      <span class="activity-mode">{{ activity.mode }}</span>
    </div>
    <p class="activity-purpose">
      {{ activity.purpose }}
    </p>
    <h2>{{ activity.prompt }}</h2>
    <p>This activity type is not yet supported by the client. The server-provided turn remains authoritative.</p>
  </article>
</template>
