<script setup lang="ts">
import type { SessionInfo, TurnEnvelope } from "../api/types";

defineProps<{ session: SessionInfo | null; turn: TurnEnvelope | null }>();
</script>

<template>
  <header class="session-header">
    <div>
      <p class="eyebrow">
        Where you are
      </p>
      <h1>Learning session<span v-if="session"> #{{ session.id }}</span></h1>
      <p v-if="turn?.theory">
        {{ turn.theory.unit.title }}
      </p>
      <p v-else-if="turn?.activity?.skill">
        {{ turn.activity.skill.title }}
      </p>
      <p v-else-if="turn?.type === 'ended'">
        Session finished or paused
      </p>
      <p v-else-if="turn?.type === 'notice'">
        Session notice
      </p>
      <p v-else>
        Current server-provided turn
      </p>
    </div>
    <dl
      v-if="session"
      class="session-facts"
    >
      <div><dt>Status</dt><dd>{{ session.status }}</dd></div>
      <div><dt>Pace</dt><dd>{{ session.pace }}</dd></div>
      <div v-if="session.remaining_minutes !== null">
        <dt>Time remaining</dt><dd>{{ Math.ceil(session.remaining_minutes) }} min</dd>
      </div>
      <div v-if="turn?.activity?.position">
        <dt>Position</dt><dd>{{ turn.activity.position.index }} / {{ turn.activity.position.of }}</dd>
      </div>
    </dl>
  </header>
</template>
