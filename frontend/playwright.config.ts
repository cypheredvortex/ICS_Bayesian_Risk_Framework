import { defineConfig, devices } from '@playwright/test'

// CI runs the backend + a production preview outside Playwright (see the
// GitHub workflow); locally, Playwright starts both servers itself.
const startWebServers = !process.env.CI

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: startWebServers
    ? [
        {
          command:
            'python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000',
          cwd: '..',
          url: 'http://127.0.0.1:8000/',
          timeout: 120_000,
          reuseExistingServer: !process.env.CI,
        },
        {
          command: 'npm run dev -- --host 127.0.0.1 --port 5173',
          url: 'http://127.0.0.1:5173',
          timeout: 120_000,
          reuseExistingServer: !process.env.CI,
        },
      ]
    : undefined,
})
