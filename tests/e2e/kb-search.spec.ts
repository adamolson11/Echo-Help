import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/#/kb');
});

test('knowledge base search page loads', async ({ page }) => {
  const main = page.getByRole('main');

  await expect(page).toHaveURL(/#\/kb$/);
  await expect(main.getByRole('heading', { name: 'Knowledge Base', level: 2 })).toBeVisible();
  await expect(
    main.getByPlaceholder('Search snippets (e.g. password reset, SSO, VPN)')
  ).toBeVisible();
});

test('knowledge base returns ranked snippet results', async ({ page }) => {
  const main = page.getByRole('main');
  const query = main.getByPlaceholder('Search snippets (e.g. password reset, SSO, VPN)');
  await query.fill('password reset');

  await main.getByRole('button', { name: 'Search' }).click();

  await expect(main.getByText('No snippets found.')).toHaveCount(0);
  await expect(main.getByText(/password reset/i).first()).toBeVisible();
});

test('knowledge base search blocks empty input submission', async ({ page }) => {
  const main = page.getByRole('main');

  await expect(main.getByRole('button', { name: 'Search' })).toBeDisabled();
});