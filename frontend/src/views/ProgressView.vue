<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useLearnerStore } from "../stores/learner";
import { groupByModule, hasProgressEvidence } from "./dashboard";

const learner = useLearnerStore();
const selectedModule = ref<string | null>(null);
const progress = computed(() => learner.progress);
const modules = computed(() => progress.value === null ? [] : [...groupByModule(progress.value.skills).keys()]);
const rows = computed(() => {
  if (progress.value === null) return [];
  return selectedModule.value === null
    ? progress.value.skills
    : progress.value.skills.filter((row) => row.module === selectedModule.value);
});
const noEvidence = computed(() => progress.value !== null && !hasProgressEvidence(progress.value.skills));

async function loadProgress(): Promise<void> {
  await learner.fetchProgress();
}

onMounted(() => { void loadProgress(); });
</script>

<template>
  <section
    class="progress-page"
    aria-labelledby="progress-title"
  >
    <div class="page-intro">
      <p class="eyebrow">
        Where you are
      </p>
      <h1 id="progress-title">
        Your learning progress
      </h1>
      <p>Your mastery states and evidence come directly from the learning engine. They are qualitative, not percentages.</p>
    </div>

    <div
      v-if="learner.progressLoading && progress === null"
      class="progress-list"
      role="status"
      aria-label="Loading progress"
    >
      <div
        v-for="index in 5"
        :key="index"
        class="skeleton-row"
      />
    </div>

    <div
      v-else-if="learner.progressError && progress === null"
      class="error-card"
      role="alert"
    >
      <h2>We couldn’t load progress</h2>
      <p>{{ learner.progressError }}</p>
      <button
        type="button"
        @click="loadProgress"
      >
        Try again
      </button>
    </div>

    <template v-else-if="progress">
      <div
        v-if="learner.progressError"
        class="error-banner"
        role="alert"
      >
        <span>Showing your last progress data. {{ learner.progressError }}</span>
        <button
          type="button"
          @click="loadProgress"
        >
          Retry
        </button>
      </div>

      <section
        class="orientation-card"
        aria-label="How to use progress"
      >
        <div><h2>Why you’re here</h2><span>Review the evidence behind each skill state.</span></div>
        <div><h2>What to do now</h2><span>Choose a module or return home to continue.</span></div>
        <div><h2>What happens next</h2><span>The engine chooses future work from your recorded evidence.</span></div>
      </section>

      <div
        v-if="noEvidence"
        class="empty-card"
      >
        <h2>No evidence yet</h2>
        <p>Start a session to record learning evidence. Your progress will appear here as the engine evaluates your work.</p>
        <RouterLink
          class="button-link"
          to="/"
        >
          Start a session
        </RouterLink>
      </div>

      <template v-else>
        <div
          class="module-tabs"
          role="group"
          aria-label="Filter progress by module"
        >
          <button
            type="button"
            :aria-pressed="selectedModule === null ? 'true' : 'false'"
            :class="{ selected: selectedModule === null }"
            @click="selectedModule = null"
          >
            All modules
          </button>
          <button
            v-for="module in modules"
            :key="module"
            type="button"
            :aria-pressed="selectedModule === module ? 'true' : 'false'"
            :class="{ selected: selectedModule === module }"
            @click="selectedModule = module"
          >
            {{ module }}
          </button>
        </div>

        <p class="filter-summary">
          {{ rows.length }} skill{{ rows.length === 1 ? "" : "s" }} shown. Evidence count records demonstrated learning evidence; it is not a score.
        </p>
        <div class="progress-list">
          <article
            v-for="row in rows"
            :key="row.skill"
            class="progress-row"
            :aria-label="`${row.title}: ${row.state.replaceAll('_', ' ')}`"
          >
            <div>
              <p class="row-module">
                {{ row.module }} · {{ row.section }}
              </p><h2>{{ row.title }}</h2>
            </div>
            <span
              class="mastery-badge"
              :data-state="row.state"
            >{{ row.state.replaceAll("_", " ") }}</span>
            <p>{{ row.evidence }} evidence record{{ row.evidence === 1 ? "" : "s" }}</p>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
