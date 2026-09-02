<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useLearnerStore } from "../stores/learner";
import { useSessionStore } from "../stores/session";
import { homeScope, homeSessionAction } from "./dashboard";

const learner = useLearnerStore();
const session = useSessionStore();
const router = useRouter();
const actionError = ref<string | null>(null);

const home = computed(() => learner.home);
const scope = computed(() => home.value === null ? "" : homeScope(home.value));

async function loadHome(): Promise<void> {
  await learner.fetchHome();
}

async function enterSession(): Promise<void> {
  if (home.value === null || session.inFlight) return;
  actionError.value = null;
  try {
    const action = homeSessionAction(home.value);
    if (action.kind === "resume") {
      await session.resume(action.sessionId);
    } else {
      await session.start();
    }
    if (session.session !== null) {
      await router.push({ name: "session", params: { id: session.session.id } });
    }
  } catch (cause) {
    actionError.value = cause instanceof Error ? cause.message : "Could not start the session.";
  }
}

onMounted(() => { void loadHome(); });
</script>

<template>
  <section
    class="dashboard"
    aria-labelledby="home-title"
  >
    <div class="page-intro">
      <p class="eyebrow">
        Your learning dashboard
      </p>
      <h1 id="home-title">
        Continue your DSA learning
      </h1>
      <p>See today’s server-provided plan, your qualitative mastery, and the next action.</p>
    </div>

    <div
      v-if="learner.homeLoading && home === null"
      class="dashboard-grid"
      aria-label="Loading dashboard"
    >
      <div
        v-for="index in 3"
        :key="index"
        class="skeleton-card"
      />
    </div>

    <div
      v-else-if="learner.homeError && home === null"
      class="error-card"
      role="alert"
    >
      <h2>We couldn’t load your dashboard</h2>
      <p>{{ learner.homeError }}</p>
      <button
        type="button"
        @click="loadHome"
      >
        Try again
      </button>
    </div>

    <template v-else-if="home">
      <div
        v-if="learner.homeError"
        class="error-banner"
        role="alert"
      >
        <span>Showing your last dashboard data. {{ learner.homeError }}</span>
        <button
          type="button"
          @click="loadHome"
        >
          Retry
        </button>
      </div>

      <div class="dashboard-grid">
        <article class="dashboard-card today-card">
          <p class="eyebrow">
            Where you are
          </p>
          <h2>Today</h2>
          <p class="metric">
            {{ home.daily.completed_units }} <span>/ {{ home.daily.target_units }} units</span>
          </p>
          <p>Daily plan status: {{ home.daily.status }}.</p>
          <p v-if="home.plan.remaining_minutes !== null">
            About {{ Math.ceil(home.plan.remaining_minutes) }} minutes remain in this session plan.
          </p>
        </article>

        <article class="dashboard-card">
          <p class="eyebrow">
            Why you’re here
          </p>
          <h2>Your current learning picture</h2>
          <p class="metric">
            {{ home.progress_summary.mastered }} <span>/ {{ home.progress_summary.total_skills }} skills mastered</span>
          </p>
          <p>Mastery is shown qualitatively in your progress report, based on evidence recorded by the learning engine.</p>
          <RouterLink to="/progress">
            View progress
          </RouterLink>
        </article>

        <article class="dashboard-card action-card">
          <p class="eyebrow">
            What to do now
          </p>
          <h2>{{ home.resume.available ? "Resume your session" : "Start a session" }}</h2>
          <p v-if="home.resume.available">
            Continue the session the server has kept ready for you.
          </p>
          <p v-else>
            Begin with the next activity selected by the learning engine.
          </p>
          <button
            type="button"
            :disabled="session.inFlight"
            @click="enterSession"
          >
            {{ session.inFlight ? "Opening…" : home.resume.available ? "Resume session" : "Start session" }}
          </button>
          <p
            v-if="actionError"
            class="inline-error"
            role="alert"
          >
            {{ actionError }}
          </p>
        </article>
      </div>

      <article class="plan-card">
        <div>
          <p class="eyebrow">
            What happens next
          </p>
          <h2>Planned preview</h2>
          <p>{{ scope }}. This preview can adapt as the engine receives new evidence.</p>
        </div>
        <ol
          v-if="home.plan.items.length"
          class="plan-list"
        >
          <li
            v-for="item in home.plan.items"
            :key="`${item.skill}-${item.title}`"
          >
            <strong>{{ item.title }}</strong>
            <span>{{ item.questions }} expected check{{ item.questions === 1 ? "" : "s" }}</span>
          </li>
        </ol>
        <p
          v-else
          class="empty-copy"
        >
          No additional units are currently shown in the plan. Start or resume to receive the authoritative next activity.
        </p>
      </article>
    </template>
  </section>
</template>
