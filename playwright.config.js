// @ts-check
const { defineConfig } = require('@playwright/test');

// Use environment variable for base URL (for Docker container testing)
const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [['html'], ['list']],
  timeout: 60000,
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        headless: true,
        channel: undefined,  // Use regular chromium, not headless shell
      },
    },
  ],
  webServer: {
    command: 'echo "Server already running"',
    url: BASE_URL,
    reuseExistingServer: true,
  },
});
