import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  fullyParallel: false,
  timeout: 60000,
  expect: { timeout: 20000 },
  use: {
    baseURL: "http://127.0.0.1:18080",
    channel: process.env.CI ? undefined : "msedge",
    headless: true,
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `${process.platform === "win32" ? '".venv\\Scripts\\python.exe"' : ".venv/bin/python"} -m uvicorn scripts.dashboard_test_server:create_app --factory --host 127.0.0.1 --port 18080`,
    cwd: "..",
    url: "http://127.0.0.1:18080/health",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
