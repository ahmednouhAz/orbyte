/**
 * Playwright fixtures for chat page tests.
 *
 * Provides:
 * - Authenticated worker-user page
 * - OrbyteApiClient for API-level setup/teardown
 * - ChatPage page object (with inputBar sub-object)
 */

import { test as base, expect } from "@playwright/test";
import { loginAsWorkerUser } from "@tests/e2e/utils/auth";
import { OrbyteApiClient } from "@tests/e2e/utils/orbyteApiClient";
import { ChatPage } from "@tests/e2e/chat/ChatPage";

export const test = base.extend<{
  api: OrbyteApiClient;
  chatPage: ChatPage;
}>({
  chatPage: async ({ page }, use, testInfo) => {
    await page.context().clearCookies();
    await loginAsWorkerUser(page, testInfo.workerIndex);
    const chatPage = new ChatPage(page);
    await use(chatPage);
  },

  api: async ({ chatPage }, use) => {
    const client = new OrbyteApiClient(chatPage.page.request);
    await use(client);
  },
});

export { expect };
