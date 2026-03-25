import { expect, test } from "@playwright/test";

const askEchoQuery = "password reset doesn't work";
const knowledgeBaseQuery = "vpn";

test("Ask Echo returns an answer for a seeded support question", async ({ page }) => {
  await page.goto("/#/ask");
  const main = page.locator("main");

  const askResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/ask-echo") &&
      response.request().method() === "POST" &&
      response.status() === 200,
  );

  await main.getByPlaceholder("Ask Echo a question about tickets...").fill(askEchoQuery);
  await main.getByRole("button", { name: "Ask Echo" }).click();

  const askResponse = await askResponsePromise;
  const payload = (await askResponse.json()) as {
    answer?: string;
  };

  expect(payload.answer?.trim()).toBeTruthy();
  await expect(main.locator(".ask-echo__answer")).toContainText(String(payload.answer));
  await expect(main.getByText("Feedback", { exact: true })).toBeVisible();
});

test("Ask Echo feedback persists after a successful answer", async ({ page, request, baseURL }) => {
  await page.goto("/#/ask");
  const main = page.locator("main");

  const askResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/ask-echo") &&
      response.request().method() === "POST" &&
      response.status() === 200,
  );

  await main.getByPlaceholder("Ask Echo a question about tickets...").fill(askEchoQuery);
  await main.getByRole("button", { name: "Ask Echo" }).click();

  const askResponse = await askResponsePromise;
  const askPayload = (await askResponse.json()) as {
    ask_echo_log_id?: number;
  };

  expect(askPayload.ask_echo_log_id).toBeTruthy();

  const feedbackResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/ask-echo/feedback") &&
      response.request().method() === "POST" &&
      response.status() === 200,
  );

  await main.getByRole("button", { name: "👍 Yes" }).click();

  const feedbackResponse = await feedbackResponsePromise;
  const feedbackPayload = (await feedbackResponse.json()) as {
    ask_echo_log_id?: number;
    helped?: boolean;
  };

  expect(feedbackPayload.ask_echo_log_id).toBe(askPayload.ask_echo_log_id);
  expect(feedbackPayload.helped).toBe(true);
  await expect(main.getByText("Saved")).toBeVisible();

  const inspectionResponse = await request.get(
    `${baseURL}/api/ask-echo/feedback/records?limit=25`,
  );
  expect(inspectionResponse.ok()).toBeTruthy();

  const inspectionPayload = (await inspectionResponse.json()) as {
    items?: Array<{ ask_echo_log_id?: number; feedback_status?: string }>;
  };
  expect(
    inspectionPayload.items?.some(
      (item) =>
        item.ask_echo_log_id === askPayload.ask_echo_log_id &&
        item.feedback_status === "helped",
    ),
  ).toBeTruthy();
});

test("Knowledge Base search shows ranked results and snippet content", async ({ page }) => {
  await page.goto("/#/kb");
  const main = page.locator("main");

  const kbResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/snippets/search") &&
      response.request().method() === "GET" &&
      response.status() === 200,
  );

  await main
    .getByPlaceholder("Search snippets (e.g. password reset, SSO, VPN)")
    .fill(knowledgeBaseQuery);
  await main.getByRole("button", { name: "Search" }).click();

  const kbResponse = await kbResponsePromise;
  const kbPayload = (await kbResponse.json()) as Array<{
    title?: string;
    content_md?: string | null;
    summary?: string | null;
  }>;

  expect(kbPayload.length).toBeGreaterThan(0);
  expect(kbPayload[0]?.title?.trim()).toBeTruthy();
  expect((kbPayload[0]?.content_md ?? kbPayload[0]?.summary ?? "").trim()).toBeTruthy();

  await expect(main.getByText(String(kbPayload[0]?.title))).toBeVisible();
  await expect(
    main.getByText(String(kbPayload[0]?.content_md ?? kbPayload[0]?.summary), { exact: false }),
  ).toBeVisible();
});

test("KB search blocks empty input without firing a request", async ({ page }) => {
  await page.goto("/#/kb");
  const main = page.locator("main");

  const searchButton = main.getByRole("button", { name: "Search" });
  await expect(searchButton).toBeDisabled();
});

test("Ask Echo shows loading state for slow responses and recovers from interrupted requests", async ({
  page,
}) => {
  await page.goto("/#/ask");
  const main = page.locator("main");

  await page.route("**/api/ask-echo", async (route) => {
    const requestBody = route.request().postDataJSON() as { q?: string };
    if (requestBody.q === "slow-response-case") {
      await new Promise((resolve) => setTimeout(resolve, 1_200));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ask_echo_log_id: 999001,
          query: requestBody.q,
          answer: "Delayed but successful answer",
          answer_kind: "grounded",
          suggested_tickets: [],
          suggested_snippets: [],
          kb_backed: false,
          kb_confidence: 0.91,
          mode: "kb_answer",
          references: [],
          reasoning: null,
          evidence: [],
          kb_evidence: [],
        }),
      });
      return;
    }

    if (requestBody.q === "interrupt-case") {
      await route.abort("failed");
      return;
    }

    await route.continue();
  });

  await main.getByPlaceholder("Ask Echo a question about tickets...").fill("slow-response-case");
  await main.getByRole("button", { name: "Ask Echo" }).click();
  await expect(main.getByText("Thinking…")).toBeVisible();
  await expect(main.locator(".ask-echo__answer")).toContainText("Delayed but successful answer");

  await main.getByPlaceholder("Ask Echo a question about tickets...").fill("interrupt-case");
  await main.getByRole("button", { name: "Ask Echo" }).click();
  await expect(main.getByText("Backend not running")).toBeVisible();
  await expect(main.getByRole("button", { name: "Details" })).toBeVisible();
});
