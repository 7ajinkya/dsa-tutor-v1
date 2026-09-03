<script setup lang="ts">
import { computed, hasInjectionContext, inject, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { piniaSymbol } from "pinia";
import type { Activity } from "../api/types";
import { useSessionStore } from "../stores/session";


const props = defineProps<{
  activity: Activity;
  busy?: boolean;
}>();

const emit = defineEmits<{
  reveal: [];
}>();

const hasPinia = hasInjectionContext() && inject(piniaSymbol, null) !== null;
const sessionStore = hasPinia ? useSessionStore() : null;


const isOpen = ref(false);
const isRequesting = ref(false);
const isExhausted = ref(false);
const hintError = ref<string | null>(null);

const canHint = computed(() => props.activity.available_actions?.includes("hint") ?? false);

const turnHint = computed(() => sessionStore?.turn?.hint ?? null);

const canReveal = computed(() =>
  props.activity.available_actions?.includes("solution") ?? false
);

const isLadderExhausted = computed(() =>
  isExhausted.value || sessionStore?.error?.code === "LADDER_EXHAUSTED"
);

const hintBadge = computed(() => {
  if (!turnHint.value) return "";
  return `Hint ${turnHint.value.level}/${props.activity.hints.max_level}`;
});

async function requestNextHint(): Promise<void> {
  if (!sessionStore || isRequesting.value || props.busy || sessionStore.inFlight) return;
  isRequesting.value = true;
  hintError.value = null;
  try {
    await sessionStore.requestHint();
  } catch (err: unknown) {
    const code = (err as { code?: string })?.code;
    if (code === "LADDER_EXHAUSTED" || sessionStore.error?.code === "LADDER_EXHAUSTED") {
      isExhausted.value = true;
    } else {
      hintError.value = err instanceof Error ? err.message : "Failed to request hint.";
    }
  } finally {
    isRequesting.value = false;
  }
}

function openDrawer(): void {
  isOpen.value = true;
}

function closeDrawer(): void {
  isOpen.value = false;
}

/** C9: Escape dismisses the open drawer (no keyboard trap); focus returns to
 *  the toggle so keyboard users keep their place. */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape" && isOpen.value) {
    event.stopPropagation();
    closeDrawer();
  }
}

watch(isOpen, async (open) => {
  if (open) {
    window.addEventListener("keydown", onKeydown);
    await nextTick();
    document.querySelector<HTMLElement>(".hint-close-btn")?.focus();
  } else {
    window.removeEventListener("keydown", onKeydown);
    await nextTick();
    document.querySelector<HTMLElement>(".hint-toggle-btn")?.focus();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onKeydown);
});

function onRevealCta(): void {
  emit("reveal");
}

watch(() => props.activity.id, () => {
  isExhausted.value = false;
  hintError.value = null;
  isOpen.value = false;
});

defineExpose({
  openDrawer,
  closeDrawer,
  requestNextHint,
  onRevealCta,
  isOpen,
  isExhausted,
  isRequesting,
});
</script>


<template>
  <div
    v-if="canHint"
    class="hint-container"
  >
    <button
      type="button"
      class="hint-toggle-btn secondary-button"
      :disabled="busy || isRequesting || sessionStore?.inFlight"
      aria-haspopup="dialog"
      :aria-expanded="isOpen"
      @click="openDrawer"
    >
      <span>Hint</span>
      <span
        v-if="hintBadge"
        class="hint-badge"
      >{{ hintBadge }}</span>
    </button>

    <div
      v-if="isOpen"
      class="hint-drawer-backdrop"
      aria-hidden="true"
      @click="closeDrawer"
    />

    <aside
      v-if="isOpen"
      class="hint-drawer"
      role="region"
      aria-label="Hints"
    >
      <div class="hint-drawer-header">
        <div class="hint-title-group">
          <h3>Hints</h3>
          <span
            v-if="turnHint"
            class="hint-level-tag"
          >
            Hint {{ turnHint.level }}/{{ activity.hints.max_level }}
          </span>
        </div>
        <button
          type="button"
          class="hint-close-btn"
          aria-label="Close hints"
          @click="closeDrawer()"
        >
          ✕
        </button>
      </div>

      <div class="hint-drawer-body">
        <!-- Exhausted State -> Reveal CTA -->
        <div
          v-if="isLadderExhausted"
          class="ladder-exhausted-card"
          role="alert"
        >
          <p class="exhausted-message">
            All hints for this activity have been exhausted.
          </p>
          <p class="exhausted-subtext">
            You can reveal the complete solution to unblock yourself. Revealing will mark this attempt as assisted.
          </p>
          <button
            v-if="canReveal"
            type="button"
            class="reveal-cta-btn primary-button"
            :disabled="busy || sessionStore?.inFlight"
            @click="onRevealCta"
          >
            Reveal solution
          </button>
        </div>

        <!-- Active Hint Display -->
        <div
          v-else-if="turnHint"
          class="active-hint-card"
        >
          <div class="hint-kind-row">
            <span class="hint-kind-chip">{{ turnHint.kind }}</span>
            <span class="hint-level-label">Hint {{ turnHint.level }}</span>
          </div>
          <p class="hint-text">
            {{ turnHint.text }}
          </p>
          <div class="hint-actions">
            <button
              type="button"
              class="secondary-button next-hint-btn"
              :disabled="isRequesting || busy || sessionStore?.inFlight"
              @click="requestNextHint"
            >
              {{ isRequesting
                ? "Getting hint…"
                : `Next hint (${turnHint.level + 1}/${activity.hints.max_level})`
              }}
            </button>
          </div>
        </div>

        <!-- No hint yet state -->
        <div
          v-else
          class="hint-intro-card"
        >
          <p>Stuck on this problem? Requesting a hint offers progressive nudges while tracking your assistance level.</p>
          <button
            type="button"
            class="primary-button get-first-hint-btn"
            :disabled="isRequesting || busy || sessionStore?.inFlight"
            @click="requestNextHint"
          >
            {{ isRequesting ? "Getting hint…" : "Get a hint" }}
          </button>
        </div>

        <p
          v-if="hintError"
          class="hint-error-message"
          role="alert"
        >
          {{ hintError }}
        </p>
      </div>
    </aside>
  </div>
</template>
