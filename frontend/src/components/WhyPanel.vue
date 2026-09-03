<script setup lang="ts">
defineProps<{ reasons: string[] }>();
</script>

<template>
  <aside
    class="why-panel"
    aria-labelledby="why-title"
  >
    <p class="eyebrow">
      Why am I doing this?
    </p>
    <h2 id="why-title">
      Why this step
    </h2>
    <ul v-if="reasons.length">
      <li
        v-for="reason in reasons"
        :key="reason"
      >
        {{ reason }}
      </li>
    </ul>
    <p v-else>
      The server has not provided a step explanation for this turn.
    </p>
  </aside>
</template>
