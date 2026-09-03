<script setup lang="ts">
import { useUiStore } from "../stores/ui";

// C8: renders the transient toasts owned by useUiStore. The stale-activity
// recovery notice ("Skipped ahead...") surfaces here as a learner-facing
// informational toast; no session state lives in this component.
const ui = useUiStore();
</script>

<template>
  <div
    class="toast-host"
    aria-live="polite"
  >
    <div
      v-for="toast in ui.toasts"
      :key="toast.id"
      class="toast"
      :class="`toast-${toast.kind}`"
    >
      <span>{{ toast.text }}</span>
      <button
        type="button"
        class="toast-dismiss"
        aria-label="Dismiss notification"
        @click="ui.dismissToast(toast.id)"
      >
        ?
      </button>
    </div>
  </div>
</template>

<style scoped>
.toast-host {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 50;
}
.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.9rem;
  border: 1px solid #cccccc;
  background: #ffffff;
  max-width: 22rem;
}
.toast-info { border-left: 4px solid #2563eb; }
.toast-success { border-left: 4px solid #16a34a; }
.toast-warning { border-left: 4px solid #d97706; }
.toast-error { border-left: 4px solid #dc2626; }
.toast-dismiss {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
}
</style>
