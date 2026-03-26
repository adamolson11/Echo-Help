import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/#/ask');
});

test('ask echo page loads', async ({ page }) => {
  const main = page.getByRole('main');

  await expect(page).toHaveURL(/#\/ask$/);

  await expect(
    main.getByRole('heading', { name: 'Ask Echo', level: 1 })
  ).toBeVisible();

  await expect(
    main.getByPlaceholder('Ask Echo about a ticket pattern, outage, or known fix')
  ).toBeVisible();
});

test('ask echo returns a response', async ({ page }) => {
  const main = page.getByRole('main');

  await main
    .getByPlaceholder('Ask Echo about a ticket pattern, outage, or known fix')
    .fill('password reset does not work');

  await main.getByRole('button', { name: 'Ask Echo' }).click();

  await expect(main.locator('.ask-echo__card--answer')).toBeVisible({ timeout: 15000 });
  await expect(main.locator('.ask-echo__card--sources')).toBeVisible({ timeout: 15000 });
  await expect(main.locator('.ask-echo__answer')).not.toHaveText('', { timeout: 15000 });
});

test('ask echo feedback persists without crashing', async ({ page, request }) => {
  const query = `password reset does not work ${Date.now()}`;
  const main = page.getByRole('main');

  await main
    .getByPlaceholder('Ask Echo about a ticket pattern, outage, or known fix')
    .fill(query);

  await main.getByRole('button', { name: 'Ask Echo' }).click();
  await expect(main.locator('.ask-echo__card--sources')).toBeVisible({ timeout: 15000 });

  await main.getByRole('button', { name: 'Helpful' }).click();
  await expect(main.getByText('Saved')).toBeVisible();

  const response = await request.get('http://127.0.0.1:8001/api/insights/ask-echo-feedback?limit=20');
  expect(response.ok()).toBeTruthy();

  const payload = (await response.json()) as {
    items?: Array<{ query_text?: string | null; helped?: boolean | null }>;
  };

  expect(
    payload.items?.some((item) => item.query_text === query && item.helped === true)
  ).toBeTruthy();
});

test('ask echo shows loading state for a slow response', async ({ page }) => {
  const main = page.getByRole('main');

  await page.route('**/api/ask-echo', async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    await route.continue();
  });

  await main
    .getByPlaceholder('Ask Echo about a ticket pattern, outage, or known fix')
    .fill('password reset does not work');

  await main.getByRole('button', { name: 'Ask Echo' }).click();
  await expect(main.getByText('Thinking…')).toBeVisible();
  await expect(main.locator('.ask-echo__card--sources')).toBeVisible({ timeout: 15000 });
});

test('ask echo surfaces backend failures clearly', async ({ page }) => {
  const main = page.getByRole('main');

  await page.route('**/api/ask-echo', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'Injected failure' }),
    });
  });

  await main
    .getByPlaceholder('Ask Echo about a ticket pattern, outage, or known fix')
    .fill('password reset does not work');

  await main.getByRole('button', { name: 'Ask Echo' }).click();

  await expect(main.getByText('Echo hit an error')).toBeVisible();
  await expect(main.getByRole('button', { name: 'Try again' })).toBeVisible();
});
