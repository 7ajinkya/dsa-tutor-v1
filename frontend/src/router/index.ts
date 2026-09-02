import { createRouter, createWebHistory } from "vue-router";

// Route map per plans/V1_SLICE_1C_PLAN.md §4 (reviewer decision D2).
// Stub views exist so the C1 scaffold compiles and the map is verifiable;
// their content is implemented in milestones C4/C5.
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "home", component: () => import("../views/HomeView.vue") },
    {
      path: "/session/:id",
      name: "session",
      component: () => import("../views/SessionView.vue"),
    },
    { path: "/progress", name: "progress", component: () => import("../views/ProgressView.vue") },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: () => import("../views/NotFoundView.vue"),
    },
  ],
});

export default router;
