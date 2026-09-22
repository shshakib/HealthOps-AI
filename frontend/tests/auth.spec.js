import { test, expect } from "@playwright/test";

const password = "isolated-browser-test-password";
async function signIn(page, username) {
  await page.goto("/");
  await page.getByLabel("Username", { exact: true }).fill(username);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account-bar")).toContainText(username);
}

test("login, viewer restrictions, and logout protect the workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Sign in to HealthOps" }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/patients")).status()).toBe(401);
  await page.screenshot({ path: "../.local/auth-login.png", fullPage: true });
  await signIn(page, "ui-viewer");
  await expect(
    page.getByRole("button", { name: "Settings", exact: true }),
  ).toHaveCount(0);
  expect(
    (
      await page.request.post("/api/v1/assistant/settings", {
        headers: { "X-HealthOps-Request": "1" },
        data: { provider: "offline", model: "" },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await page.request.post("/api/v1/admin/evaluations", {
        headers: { "X-HealthOps-Request": "1" },
        data: { limit: 1 },
      })
    ).status(),
  ).toBe(403);
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await expect(
    page.getByRole("button", { name: "Run screening", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Manage users", exact: true }),
  ).toHaveCount(0);
  expect(
    (
      await page.request.post("/api/v1/screenings", {
        headers: { "X-HealthOps-Request": "1" },
        data: {},
      })
    ).status(),
  ).toBe(403);
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Sign in to HealthOps" }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/patients")).status()).toBe(401);
});

test("reviewer identity is fixed and AI configuration stays administrator-only", async ({
  page,
}) => {
  await signIn(page, "ui-reviewer");
  await expect(
    page.getByRole("button", { name: "Settings", exact: true }),
  ).toHaveCount(0);
  expect(
    (
      await page.request.post("/api/v1/assistant/settings", {
        headers: { "X-HealthOps-Request": "1" },
        data: { provider: "offline", model: "" },
      })
    ).status(),
  ).toBe(403);
  expect(
    (
      await page.request.post("/api/v1/admin/evaluations", {
        headers: { "X-HealthOps-Request": "1" },
        data: { limit: 1 },
      })
    ).status(),
  ).toBe(403);
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  await expect(page.locator(".review-form")).toContainText("ui-reviewer");
  await expect(page.getByLabel("Reviewer label")).toHaveCount(0);
  await expect(
    page.getByText("Model connection settings", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("radio", { name: /Request information/ }).check();
  await page
    .getByRole("textbox", { name: "Reason", exact: true })
    .fill("Browser test: request manual review of synthetic evidence.");
  await page.locator(".review-form").getByRole("checkbox").check();
  await page.locator(".review-form").getByRole("button").click();
  await expect(page.locator(".timeline-item").first()).toContainText(
    "ui-reviewer",
  );
});

test("administrator creates a viewer, who can change their password", async ({
  page,
}) => {
  const username = `created-${Date.now()}`;
  await signIn(page, "ui-admin");
  await page.getByRole("button", { name: "Manage users", exact: true }).click();
  await page.getByLabel("New username", { exact: true }).fill(username);
  await page.getByLabel("Initial password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page.getByRole("status")).toHaveText("Account created.");
  await page.screenshot({ path: "../.local/auth-users.png", fullPage: true });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await signIn(page, username);
  await page
    .getByRole("button", { name: "Change password", exact: true })
    .click();
  await page.getByLabel("Current password", { exact: true }).fill(password);
  await page
    .getByLabel("New password", { exact: true })
    .fill(`${password}-changed`);
  await page
    .getByRole("button", { name: "Change password and sign out", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Sign in to HealthOps" }),
  ).toBeVisible();
  await page
    .getByLabel("Password", { exact: true })
    .fill(`${password}-changed`);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account-bar")).toContainText(username);
});
