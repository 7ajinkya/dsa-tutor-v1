<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import SessionHeader from "../components/SessionHeader.vue";
import ActivityDispatcher from "../components/activity/ActivityDispatcher.vue";
import ResultCard from "../components/ResultCard.vue";
import TheoryPanel from "../components/TheoryPanel.vue";
import WhyPanel from "../components/WhyPanel.vue";
import { useSessionStore } from "../stores/session";
import {
  currentSessionMatches, defensiveTurnLabel, endedSummary,
  routeSessionId,
} from "./sessionView";

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();
const localError = ref<string | null>(null);
const activityError = ref<string | null>(null);
const turn = computed(() => sessionStore.turn);
const session = computed(() => sessionStore.session);
const isLoading = computed(() => sessionStore.status === "loading" || sessionStore.inFlight);
const reasons = computed(() => turn.value?.step?.why ?? []);
const invalidSession = computed(() => routeSessionId(route.params.id) === null);
const ended = computed(() =>
  turn.value?.type === "ended"
    ? endedSummary(turn.value, session.value)
    : null,
);
/** C8: retry affordance — only for retryable failures of the last answer; the
 *  store keeps the same Idempotency-Key so the server can deduplicate. */
const retryableAnswer = computed(() =>
  sessionStore.error !== null
  && sessionStore.error.retryable
  && sessionStore.lastSubmission !== null,
);

// C8 cleanup (F11): a view-local submission error belongs to one turn only.
// Once the server supplies a different authoritative turn (retry succeeded,
// hint advanced the turn, reload, ...), the stale message must not linger.
watch(() => sessionStore.turn, () => { activityError.value = null; });

async function loadRouteSession(): Promise<void> {
  localError.value = null;
  const id = routeSessionId(route.params.id);
  if (id === null) return;
  if (currentSessionMatches(session.value, id) && turn.value !== null) return;
  try {
    await sessionStore.loadSnapshot(id);
  } catch (cause) {
    localError.value = cause instanceof Error ? cause.message : "Could not load this session.";
  }
}

async function acknowledgeTheory(): Promise<void> {
  if (isLoading.value || turn.value?.type !== "theory") return;
  localError.value = null;
  try {
    await sessionStore.theorySeen();
  } catch (cause) {
    localError.value = cause instanceof Error ? cause.message : "Could not record this study turn.";
  }
}

async function retryLastAnswer(): Promise<void> {
  const submission = sessionStore.lastSubmission;
  if (isLoading.value || submission === null) return;
  activityError.value = null;
  try {
    await sessionStore.submitAnswer(submission.activityId, submission.answer);
  } catch (cause) {
    activityError.value = cause instanceof Error ? cause.message : "Could not submit this answer.";
  }
}

async function submitActivity(answer: string): Promise<void> {
  if (isLoading.value || turn.value?.type !== "activity" || turn.value.activity === null) return;
  activityError.value = null;
  try {
    await sessionStore.submitAnswer(turn.value.activity.id, answer);
  } catch (cause) {
    activityError.value = cause instanceof Error ? cause.message : "Could not submit this answer.";
  }
}

/** C8 cleanup (F9): resume CTA of the ended screen (paused sessions only). */
async function resumeEndedSession(): Promise<void> {
  const id = session.value?.id;
  if (isLoading.value || id === null || id === undefined) return;
  localError.value = null;
  try {
    await sessionStore.resume(id);
  } catch (cause) {
    localError.value = cause instanceof Error ? cause.message : "Could not resume this session.";
  }
}

function goHome(): void { void router.push({ name: "home" }); }

watch(() => route.params.id, () => { void loadRouteSession(); }, { immediate: true });
</script>

<template>
  <section
    class="session-page"
    aria-labelledby="session-page-title"
  >
    <div
      v-if="invalidSession"
      class="error-card"
      role="alert"
    >
      <h1 id="session-page-title">
        This session link is invalid
      </h1>
      <p>Session ids are supplied by the server. Return home to start or resume a valid session.</p>
      <button
        type="button"
        @click="goHome"
      >
        Back to Home
      </button>
    </div>

    <template v-else>
      <div
        v-if="isLoading && turn === null"
        class="session-loading"
        aria-label="Loading session"
      >
        <div class="skeleton-card" /><div class="skeleton-card" />
      </div>
      <div
        v-else-if="(localError || sessionStore.error) && turn === null"
        class="error-card"
        role="alert"
      >
        <h1 id="session-page-title">
          We couldn’t load this session
        </h1>
        <p>{{ localError ?? sessionStore.error?.message }}</p>
        <button
          type="button"
          @click="loadRouteSession"
        >
          Try again
        </button>
        <button
          class="secondary-button"
          type="button"
          @click="goHome"
        >
          Back to Home
        </button>
      </div>
      <template v-else-if="turn">
        <SessionHeader
          :session="session"
          :turn="turn"
        />
        <WhyPanel :reasons="reasons" />
        <div
          v-if="localError || sessionStore.error"
          class="error-banner"
          role="alert"
        >
          <span>{{ localError ?? sessionStore.error?.message }}</span>
          <button
            type="button"
            @click="loadRouteSession"
          >
            Retry
          </button>
        </div>

        <TheoryPanel
          v-if="turn.type === 'theory' && turn.theory"
          :theory="turn.theory"
          :busy="isLoading"
          @acknowledge="acknowledgeTheory"
        />
        <template v-else-if="turn.type === 'activity' && turn.activity">
          <ResultCard
            v-if="sessionStore.lastResult"
            :result="sessionStore.lastResult"
          />
          <div
            v-if="retryableAnswer"
            class="error-banner"
            role="alert"
          >
            <span>A temporary issue interrupted your answer. Your answer is kept — you can retry it.</span>
            <button
              type="button"
              @click="retryLastAnswer"
            >
              Retry answer
            </button>
          </div>
          <ActivityDispatcher
            :key="turn.activity.id"
            :activity="turn.activity"
            :busy="isLoading"
            :error="activityError"
            @submit="submitActivity"
          />
        </template>
        <template v-else-if="turn.type === 'ended'">
          <article
            v-if="ended"
            class="turn-ended"
            aria-labelledby="ended-title"
          >
            <p class="eyebrow">
              What do I do now?
            </p>
            <h2 id="ended-title">
              {{ ended.badge === "paused" ? "Session paused" : "Session ended" }}
            </h2>
            <p
              v-if="ended.reasonCode"
              class="muted"
            >
              <span
                class="ended-reason-badge"
              >{{ ended.reasonCode }}</span>
            </p>
            <p>{{ ended.detail }}</p>
            <p
              v-if="session?.units_completed"
              class="muted"
            >
              Units completed this session: {{ session.units_completed }}
            </p>
            <button
              v-if="ended.showResumeCta"
              type="button"
              @click="resumeEndedSession"
            >
              Resume session
            </button>
            <button
              type="button"
              @click="goHome"
            >
              Back to Home
            </button>
          </article>
        </template>
        <article
          v-else
          class="turn-notice"
        >
          <p class="eyebrow">
            What do I do now?
          </p>
          <h2>{{ turn.activity?.purpose ?? turn.notice?.kind ?? "Current server turn" }}</h2>
          <p>{{ defensiveTurnLabel(turn) }}</p>
          <p v-if="turn.activity?.prompt">
            {{ turn.activity.prompt }}
          </p>
          <p class="empty-copy">
            This turn is displayed as server metadata until its dedicated interaction surface is available.
          </p>
        </article>
      </template>
      <div
        v-else
        class="error-card"
        role="alert"
      >
        <h1 id="session-page-title">
          No current turn is available
        </h1>
        <p>The server did not provide a renderable turn for this session.</p>
        <button
          type="button"
          @click="loadRouteSession"
        >
          Try again
        </button>
        <button
          class="secondary-button"
          type="button"
          @click="goHome"
        >
          Back to Home
        </button>
      </div>
    </template>
  </section>
</template>
