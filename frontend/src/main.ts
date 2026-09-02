import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./style.css";

// C1 scaffold (plans/V1_SLICE_1C_PLAN.md milestone C1).
// API client (C2), stores (C3), views (C4/C5) build on this skeleton.
const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");
