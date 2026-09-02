/**
 * useLearnerStore (design §6): home dashboard + qualitative progress data and
 * their fetch actions. Read-only — mutations live in useSessionStore.
 */
import { ref } from "vue";
import { defineStore } from "pinia";
import * as api from "../api/endpoints";
import type { HomePayload, ProgressReport } from "../api/types";

export const useLearnerStore = defineStore("learner", () => {
  const home = ref<HomePayload | null>(null);
  const progress = ref<ProgressReport | null>(null);
  const homeLoading = ref(false);
  const progressLoading = ref(false);
  const homeError = ref<string | null>(null);
  const progressError = ref<string | null>(null);

  /** Home is read-only composition — safe to refetch at any time. */
  async function fetchHome(): Promise<void> {
    homeLoading.value = true;
    homeError.value = null;
    try {
      home.value = await api.home();
    } catch (cause) {
      homeError.value = cause instanceof Error ? cause.message : "Failed to load home.";
    } finally {
      homeLoading.value = false;
    }
  }

  async function fetchProgress(): Promise<void> {
    progressLoading.value = true;
    progressError.value = null;
    try {
      progress.value = await api.progress();
    } catch (cause) {
      progressError.value = cause instanceof Error ? cause.message : "Failed to load progress.";
    } finally {
      progressLoading.value = false;
    }
  }

  return {
    home, progress, homeLoading, progressLoading, homeError, progressError,
    fetchHome, fetchProgress,
  };
});
