import { defineConfig, devices } from "@playwright/test";

// C10 (plan A20 L3 / A22): Playwright journeys against the REAL V1 backend.
// The backend runs in --offline mode: the genuine FastAPI adapter + engine with
// in-memory storage (no MySQL prerequisite, nothing mocked, fresh state per run).
const BACKEND = "http://127.0.0.1:8000";
// Vite 8 binds localhost (IPv6 ::1 on this machine), so use the hostname, not 127.0.0.1.
const FRONTEND = "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  // The journeys share one deterministic server-side session lifecycle.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 45_000,
  expect: { timeout: 7_000 },
  reporter: [["list"]],
  use: {
    baseURL: FRONTEND,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: ".venv\\Scripts\\python.exe -m dsa_tutor.api --offline --port 8000",
      url: `${BACKEND}/api/v1/home`,
      cwd: "..",
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: "npm run dev -- --port 5173 --strictPort",
      url: FRONTEND,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } },
    { name: "webkit", use: { ...devices["Desktop Safari"], viewport: { width: 1280, height: 800 } } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
});