import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page, request }) => {
  const options = {
    headers: { "X-HealthOps-Request": "1" },
    data: { username: "ui-admin", password: "isolated-browser-test-password" },
  };
  expect((await request.post("/api/v1/auth/login", options)).ok()).toBeTruthy();
  expect(
    (await page.request.post("/api/v1/auth/login", options)).ok(),
  ).toBeTruthy();
});

test("provider settings save and clear keys without exposing them or calling a model", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  const assistant = page.getByRole("region", { name: "Screening assistant" });
  await expect(assistant.getByLabel("AI provider")).toHaveCount(0);
  const id = page.url().split("#assessment/")[1];
  await page
    .getByRole("textbox", { name: "Reason", exact: true })
    .fill("Keep my unfinished review while configuring AI.");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "AI configuration", exact: true }),
  ).toBeVisible();
  const panel = page.getByRole("region", { name: "Model connection settings" });
  const fakeKey = "fake-ui-key-never-a-real-credential";
  for (const provider of ["openai", "anthropic", "gemini"]) {
    await panel
      .getByRole("combobox", { name: "AI provider", exact: true })
      .selectOption(provider);
    await panel
      .getByRole("textbox", { name: "Model ID", exact: true })
      .fill("test-model");
    await panel.getByLabel("Provider API key", { exact: true }).fill(fakeKey);
    await panel
      .getByRole("button", { name: "Save model settings", exact: true })
      .click();
    await expect(panel.getByRole("status")).toHaveText(
      "Settings saved. No model request was made.",
    );
    await expect(
      panel.getByLabel("Provider API key", { exact: true }),
    ).toHaveValue("");
    const status = await request.get("/api/v1/assistant/status");
    expect(await status.text()).not.toContain(fakeKey);
    expect((await status.json()).provider).toBe(provider);
    expect(
      await page.evaluate(() =>
        JSON.stringify({
          local: { ...localStorage },
          session: { ...sessionStorage },
        }),
      ),
    ).not.toContain(fakeKey);
    // The bypass must remain usable with a configured cloud key and make no model call.
    await page
      .getByRole("button", { name: "Back to workspace", exact: true })
      .click();
    await expect(assistant.locator(".assistant-mode")).toContainText(
      "configured",
    );
    await expect(
      page.getByRole("textbox", { name: "Reason", exact: true }),
    ).toHaveValue("Keep my unfinished review while configuring AI.");
    await assistant.getByRole("switch").check();
    await assistant
      .getByRole("button", { name: "Explain this screening", exact: true })
      .click();
    await expect(
      assistant.getByText("Evidence-only answer", { exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Settings", exact: true }).click();
    await panel
      .getByRole("button", { name: "Remove API key", exact: true })
      .click();
    await expect(panel.getByRole("status")).toHaveText(
      "Key removed from this server session.",
    );
    await expect(panel).toContainText("No key configured for this provider.");
  }
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../.local/provider-settings-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "../.local/provider-settings-desktop.png",
    fullPage: true,
  });
  await panel
    .getByRole("combobox", { name: "AI provider", exact: true })
    .selectOption("offline");
  await panel
    .getByRole("button", { name: "Save model settings", exact: true })
    .click();
  await expect(panel.getByRole("status")).toHaveText(
    "Settings saved. No model request was made.",
  );
  expect(
    (await (await request.get(`/api/v1/screenings/${id}`)).json()).reviews,
  ).toHaveLength(0);
});

test("admin tests a saved AI connection without an assessment and sees validation failures", async ({
  page,
  request,
}) => {
  const before = await (await request.get("/api/v1/screenings")).json();
  await page.goto("/");
  await page.getByRole("button", { name: "Settings", exact: true }).click();
  const panel = page.getByRole("region", { name: "Model connection settings" });
  const check = panel.getByRole("button", {
    name: "Test saved connection",
    exact: true,
  });
  await expect(check).toBeDisabled();
  await panel.getByLabel("AI provider", { exact: true }).selectOption("openai");
  await panel.getByLabel("Model ID", { exact: true }).fill("test-model");
  await panel
    .getByLabel("Provider API key", { exact: true })
    .fill("fake-ui-key-never-a-real-credential");
  await expect(check).toBeDisabled();
  await panel
    .getByRole("button", { name: "Save model settings", exact: true })
    .click();
  await expect(check).toBeEnabled();
  let calls = 0;
  // UI result handling is stubbed; API evaluation/permissions have separate Python tests.
  await page.route("**/api/v1/admin/evaluations", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ limit: 1 });
    calls += 1;
    await route.fulfill({ json: { passed: calls === 1 } });
  });
  await check.click();
  await expect(panel).toContainText("Connection verified.");
  await panel
    .getByLabel("Model ID", { exact: true })
    .fill("another-test-model");
  await expect(check).toBeDisabled();
  await expect(panel).not.toContainText("Connection verified.");
  await panel
    .getByRole("button", { name: "Save model settings", exact: true })
    .click();
  await check.click();
  await expect(panel.getByRole("alert")).toContainText(
    "did not complete a validated answer",
  );
  expect(calls).toBe(2);
  expect(await (await request.get("/api/v1/screenings")).json()).toEqual(
    before,
  );
  await panel
    .getByLabel("AI provider", { exact: true })
    .selectOption("offline");
  await panel
    .getByRole("button", { name: "Save model settings", exact: true })
    .click();
  await expect(check).toBeDisabled();
});

test("assistant explains saved evidence, opens citations, and leaves decisions human", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await page.getByRole("button", { name: /Synthetic demo-002 Born/ }).click();
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  const panel = page.getByRole("region", { name: "Screening assistant" });
  await expect(panel).toBeVisible();
  const id = page.url().split("#assessment/")[1];
  const before = await (await request.get(`/api/v1/screenings/${id}`)).json();
  await panel
    .getByRole("button", { name: "Explain this screening", exact: true })
    .click();
  await expect(
    panel.getByText("Evidence-only answer", { exact: true }),
  ).toBeVisible();
  await expect(panel.locator(".assistant-citation")).toHaveCount(3);
  await panel
    .getByRole("button", { name: "Recent laboratory result", exact: true })
    .click();
  await expect(page.locator("#criterion-recent_lab_in_range")).toHaveAttribute(
    "open",
    "",
  );
  await panel
    .getByRole("button", { name: "What evidence is missing?", exact: true })
    .click();
  await expect(panel.locator(".assistant-citation")).toHaveCount(1);
  await expect(panel.locator(".assistant-citation")).toContainText(
    "older than",
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await panel.screenshot({ path: "../.local/assistant-mobile.png" });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await panel.screenshot({ path: "../.local/assistant-desktop.png" });
  await panel
    .getByRole("textbox", { name: "Your question" })
    .fill("Enroll this patient now");
  await panel
    .getByRole("button", { name: "Ask assistant", exact: true })
    .click();
  await expect(panel).toContainText("I cannot make clinical decisions");
  const after = await (await request.get(`/api/v1/screenings/${id}`)).json();
  expect(after).toEqual(before);
  await panel
    .getByRole("button", { name: "Open AI settings", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "AI configuration", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Back to workspace", exact: true })
    .click();
  await expect(panel).toContainText("I cannot make clinical decisions");
  await expect(
    page.getByRole("heading", { name: "Record your decision" }),
  ).toBeVisible();
});

test("browse evidence, screen a fixture, save a review, and reopen history", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeEnabled();
  await page.screenshot({
    path: "../.local/dashboard-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "View health records" }).click();
  await expect(
    page.getByRole("dialog", { name: "Patient health records" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Search health records" })
    .fill("zz-no-such-record");
  await expect(
    page.getByText("No matching records", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Record your decision" }),
  ).toBeVisible();
  await page
    .locator("summary")
    .filter({ hasText: "Recent laboratory result" })
    .click();
  await page.locator("details[open] .evidence-links button").first().click();
  await expect(
    page.getByRole("dialog", { name: "Supporting evidence" }),
  ).toBeVisible();
  await expect(page.getByText("8.2 %", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("radio", { name: /Request information/ }).check();

  await page
    .getByRole("textbox", { name: "Reason", exact: true })
    .fill("Browser test: additional source evidence is needed.");
  await expect(
    page.getByRole("button", { name: "Save patient review" }),
  ).toBeDisabled();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Save patient review" }).click();
  await expect(page.locator(".timeline-item")).toContainText(
    "Browser test: additional source evidence is needed.",
  );
  await page.reload();
  await expect(page.locator(".timeline-item")).toContainText("ui-admin");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: /Review history/ })
    .click();
  await expect(page.getByRole("table")).toContainText("Information requested");
  await page
    .getByRole("button", { name: /Open assessment/ })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Record your decision" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("rule gate, source inspection, and interpretation review in isolated ledger", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Trial or screening exercise", exact: true })
    .selectOption("NCT06591286");
  await expect(
    page.getByText("Rule review required", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("button", { name: "Review trial rules", exact: true })
    .click();
  await page
    .locator("summary")
    .filter({ hasText: "Read complete eligibility criteria" })
    .click();
  await expect(page.locator(".source-text")).toContainText(
    "Exclusion Criteria",
  );
  await page
    .getByRole("button", { name: "Prepare draft", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Review this interpretation" }),
  ).toBeVisible();
  await page.getByRole("radio", { name: /Approve interpretation/ }).check();

  await page
    .getByRole("textbox", { name: "Reason", exact: true })
    .fill(
      "Isolated test database only: exercising the interpretation review interface.",
    );
  await page.getByRole("checkbox").check();
  await page
    .getByRole("button", { name: "Save interpretation review", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Recorded interpretation review" }),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Patient screening", exact: true })
    .click();
  await page
    .getByLabel("Approved interpretation", { exact: true })
    .selectOption({ index: 1 });
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  await expect(
    page.getByText("Full eligibility review", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Record your decision" }),
  ).toBeVisible();
});

test("mobile layout keeps navigation and forms inside viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeEnabled();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../.local/dashboard-mobile.png",
    fullPage: true,
  });
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Trial rules", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "From trial text to reviewed rules" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("a concurrent review preserves the draft and requires renewed acknowledgement", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Record your decision" }),
  ).toBeVisible();
  const id = page.url().split("#assessment/")[1];
  await page.getByRole("radio", { name: /Request information/ }).check();

  const reason = "Preserve this draft while a newer review is loaded.";
  await page.getByRole("textbox", { name: "Reason", exact: true }).fill(reason);
  await page.getByRole("checkbox").check();
  const other = await request.post(`/api/v1/screenings/${id}/reviews`, {
    headers: { "X-HealthOps-Request": "1" },
    data: {
      reviewer: "Simulated second reviewer",
      reason: "Another reviewer saved a decision first.",
      decision: "dismiss",
      expected_revision: 0,
    },
  });
  expect(other.status()).toBe(201);
  await page.getByRole("button", { name: "Save patient review" }).click();
  await expect(page.getByRole("alert")).toContainText("newer review");
  await expect(
    page.getByRole("textbox", { name: "Reason", exact: true }),
  ).toHaveValue(reason);
  await expect(page.getByRole("checkbox")).not.toBeChecked();
  await expect(page.locator(".timeline-item")).toContainText(
    "Another reviewer saved",
  );
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Save patient review" }).click();
  await expect(page.locator(".timeline-item")).toHaveCount(2);
});
