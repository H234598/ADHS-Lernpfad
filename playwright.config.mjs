import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests/web",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  retries: 0,
  workers: 1,
  outputDir: "build/playwright-results",
  reporter: [["line"]],
  use: {
    baseURL: "http://127.0.0.1:8765",
    browserName: "chromium",
    headless: true,
    reducedMotion: "reduce",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: {
    command: "python3 -m http.server 8765 --directory site",
    url: "http://127.0.0.1:8765/knowledge-graph/",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
