<script setup lang="ts">
import ToastHost from "./components/ToastHost.vue";
</script>

<template>
  <header class="app-header">
    <span class="app-title">DSA Tutor</span>
    <nav
      class="app-nav"
      aria-label="Main navigation"
    >
      <RouterLink to="/">
        Home
      </RouterLink>
      <RouterLink to="/progress">
        Progress
      </RouterLink>
    </nav>
  </header>
  <main class="app-main">
    <RouterView />
  </main>
  <ToastHost />
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e2e2;
}
.app-title {
  font-weight: 700;
}
.app-nav {
  display: flex;
  gap: 0.75rem;
}
.app-main {
  padding: 1rem;
}
.app-nav a {
  padding: 0.35rem 0.5rem;
}
/* C9: header wraps and nav stays tappable on narrow screens. */
@media (max-width: 768px) {
  .app-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.4rem;
    padding: 0.65rem 1rem;
  }
  .app-nav {
    flex-wrap: wrap;
    gap: 0.25rem;
  }
  .app-main {
    padding: 0.75rem 0.75rem 2rem;
  }
}
</style>
