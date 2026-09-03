<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import SessionHeader from "../components/SessionHeader.vue";
import TheoryPanel from "../components/TheoryPanel.vue";
import WhyPanel from "../components/WhyPanel.vue";
import { useSessionStore } from "../stores/session";
import { currentSessionMatches, defensiveTurnLabel, routeSessionId } from "./sessionView";

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();
const localError = ref<string | null>(null);
const turn = computed(() => sessionStore.turn);
const session = computed(() => sessionStore.session);
const isLoading = computed(() => sessionStore.status === "loading" || sessionStore.inFlight);
const reasons = computed(() => turn.value?.step?.why ?? []);
const invalidSession = computed(() => routeSessionId(route.params.id) === null);

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
