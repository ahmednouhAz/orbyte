/**
 * Playwright fixtures for Admin Groups page tests.
 *
 * Provides:
 * - Authenticated admin page
 * - OrbyteApiClient for API-level setup/teardown
 * - GroupsAdminPage page object
 */

import { test as base, expect, type Page } from "@playwright/test";
import { loginAs } from "@tests/e2e/utils/auth";
import { OrbyteApiClient } from "@tests/e2e/utils/orbyteApiClient";
import { GroupsAdminPage } from "./GroupsAdminPage";

export const test = base.extend<{
  adminPage: Page;
  api: OrbyteApiClient;
  groupsPage: GroupsAdminPage;
}>({
  adminPage: async ({ page }, use) => {
    await page.context().clearCookies();
    await loginAs(page, "admin");
    await use(page);
  },

  api: async ({ adminPage }, use) => {
    const client = new OrbyteApiClient(adminPage.request);
    await use(client);
  },

  groupsPage: async ({ adminPage }, use) => {
    const groupsPage = new GroupsAdminPage(adminPage);
    await use(groupsPage);
  },
});

export { expect };
