import { expect, test } from "@playwright/test";

const askEchoQuery = "password reset doesn't work";
const knowledgeBaseQuery = "vpn";
const slowResponseDelayMs = 1_200;

test("Ask Echo returns an answer for a seeded support question", async ({ page }) => {
  await page.goto("/#/flywheel");
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
    flywheel?: { recommendations?: Array<{ title?: string }> };
  };

  expect(payload.answer?.trim()).toBeTruthy();
  await expect(main.locator(".ask-echo__answer")).toContainText(String(payload.answer));
  expect(payload.flywheel?.recommendations?.length).toBe(3);
  await expect(main.locator(".ask-echo__card--flywheel .ask-echo__card-title")).toHaveText("2. Pick your next action");
  await expect(main.locator(".ask-echo__recommendation-card")).toHaveCount(3);
});

test("Ask Echo feedback persists after a successful answer", async ({ page, request, baseURL }) => {
  await page.goto("/#/flywheel");
  const main = page.locator("main");
  const resolvedBaseUrl = baseURL ?? "http://127.0.0.1:5174";

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

  await main.locator(".ask-echo__recommendation-card").nth(1).click();
  await main.getByRole("button", { name: /^Resolved$/ }).click();
  await main.getByLabel("Outcome notes").fill("The ticket-backed fix resolved the issue.");
  await main
    .getByLabel("What should Echo remember next time?")
    .fill("Use the ticket-backed fix first when the reset token is valid but the UI still fails.");
  await main.getByRole("button", { name: "Save learning for next time" }).click();

  const feedbackResponse = await feedbackResponsePromise;
  const feedbackPayload = (await feedbackResponse.json()) as {
    ask_echo_log_id?: number;
    helped?: boolean;
    selected_recommendation_id?: string;
    outcome?: string;
    reusable_learning?: string;
  };

  expect(feedbackPayload.ask_echo_log_id).toBe(askPayload.ask_echo_log_id);
  expect(feedbackPayload.helped).toBe(true);
  expect(feedbackPayload.selected_recommendation_id?.trim()).toBeTruthy();
  expect(feedbackPayload.outcome).toBe("resolved");
  expect(feedbackPayload.reusable_learning?.trim()).toBeTruthy();
  await expect(main.locator(".ask-echo__card--feedback .ask-echo__badge--success")).toHaveText("Saved");

  const inspectionResponse = await request.get(
    `${resolvedBaseUrl}/api/ask-echo/feedback/records?limit=25`,
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

test("Ask Echo renders clickable ticket sources and opens ticket detail", async ({ page }) => {
  await page.goto("/#/flywheel");
  const main = page.locator("main");

  const askResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/ask-echo") &&
      response.request().method() === "POST" &&
      response.status() === 200,
  );

  await main.getByPlaceholder("Ask Echo a question about tickets...").fill("password reset");
  await main.getByRole("button", { name: "Ask Echo" }).click();

  const askResponse = await askResponsePromise;
  const askPayload = (await askResponse.json()) as {
    references?: Array<{ ticket_id?: number }>;
    suggested_tickets?: Array<{ id?: number }>;
  };

  const expectedTicketId = askPayload.references?.[0]?.ticket_id ?? askPayload.suggested_tickets?.[0]?.id;
  expect(expectedTicketId).toBeTruthy();

  const sourceItems = main.locator(".ask-echo__source-item");
  await expect(sourceItems.first()).toBeVisible();
  await expect(sourceItems.first()).toHaveCSS("cursor", "pointer");

  await sourceItems.first().click();

  await expect(page).toHaveURL(new RegExp(`#\\/tickets\\/${expectedTicketId}$`));
  await expect(main.getByRole("button", { name: "Back to Ask Echo" })).toBeVisible();
  await expect(main.getByText(`Ticket #${expectedTicketId}`)).toBeVisible();
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
      await new Promise((resolve) => setTimeout(resolve, slowResponseDelayMs));
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
          flywheel: {
            issue: requestBody.q,
            state: {
              current_stage: "recommendations_ready",
              recommended_action_count: 3,
              selected_recommendation_id: null,
              outcome_recorded: false,
              reusable_learning_saved: false,
            },
            recommendations: [
              {
                id: "general-1",
                title: "Run a focused diagnostic pass",
                summary: "Collect the strongest diagnostics first.",
                rationale: "Fallback path while the backend is delayed.",
                confidence: 0.25,
                source: { kind: "general", label: "General diagnostic guidance" },
                steps: ["Capture the failure", "Check the dependency", "Escalate if needed"],
              },
              {
                id: "general-2",
                title: "Check the adjacent system",
                summary: "Verify likely dependencies.",
                rationale: "Useful second move when there is no grounded ticket.",
                confidence: 0.2,
                source: { kind: "general", label: "General diagnostic guidance" },
                steps: ["Check auth", "Check network", "Check recent changes"],
              },
              {
                id: "general-3",
                title: "Prepare an escalation packet",
                summary: "Capture the exact failed path.",
                rationale: "Keeps the loop moving if the issue is unresolved.",
                confidence: 0.15,
                source: { kind: "general", label: "General diagnostic guidance" },
                steps: ["Save the logs", "Summarize the attempt", "Route to the right owner"],
              },
            ],
            outcome_options: [
              "resolved",
              "partially_resolved",
              "not_resolved",
              "needs_escalation",
            ],
            reusable_learning_prompt:
              "Capture what Echo should remember next time: the winning step, when to use it, and any escalation signal.",
          },
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
