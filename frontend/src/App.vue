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
</style>
