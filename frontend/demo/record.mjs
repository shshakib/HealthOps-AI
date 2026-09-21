// Run against the isolated dashboard_test_server on port 18081 only.
import { chromium, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const output = path.resolve("../.local/demo");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "msedge", headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: output, size: { width: 1440, height: 1000 } },
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
await page.addInitScript(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const banner = document.createElement("div");
    banner.id = "demo-caption";
    banner.style.cssText =
      "position:fixed;bottom:0;left:0;right:0;z-index:99999;background:#102b36;color:white;padding:14px 28px;font:18px system-ui;pointer-events:none;border-top:3px solid #38c4a2;";
    banner.textContent = "AUTOMATED DEMO · SYNTHETIC DATA · SIMULATED REVIEW";
    document.body.appendChild(banner);
  });
});
async function chapter(text, seconds = 12) {
  console.log(text);
  await page.locator("#demo-caption").evaluate((el, caption) => {
    el.textContent = `AUTOMATED DEMO · SYNTHETIC DATA · SIMULATED REVIEW | ${caption}`;
  }, text);
  await page.waitForTimeout(seconds * 1000);
}

try {
  await page.goto("http://127.0.0.1:18081/");
  await page.getByLabel("Username", { exact: true }).fill("ui-reviewer");
  await page
    .getByLabel("Password", { exact: true })
    .fill("isolated-browser-test-password");
  await chapter(
    "1. Sign in with a reviewer account. Permissions are enforced by the API.",
    8,
  );
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".account-bar")).toContainText("ui-reviewer");
  await page
    .getByRole("combobox", { name: "Patient data", exact: true })
    .selectOption("fixtures");
  await page.getByRole("button", { name: /Synthetic demo-002 Born/ }).click();
  await chapter(
    "2. Select a handcrafted synthetic patient and a fictional screening exercise.",
  );
  await page.getByRole("button", { name: "View health records" }).click();
  await expect(
    page.getByRole("dialog", { name: "Patient health records" }),
  ).toBeVisible();
  await chapter("3. Inspect the recorded conditions and laboratory evidence.");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page
    .getByRole("button", { name: "Run screening", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Record your decision" }),
  ).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await chapter(
    "4. Rules produce met, not met, or unknown findings. Stale evidence stays unknown.",
  );
  await page.screenshot({ path: "../docs/images/review-workbench-v0.2.png" });
  await page
    .locator("summary")
    .filter({ hasText: "Recent laboratory result" })
    .click();
  await page.locator("details[open] .evidence-links button").first().click();
  await expect(
    page.getByRole("dialog", { name: "Supporting evidence" }),
  ).toBeVisible();
  await chapter(
    "5. Each finding links back to the evidence saved with this assessment.",
  );
  await page.getByRole("button", { name: "Close dialog" }).click();
  const assistant = page.getByRole("region", { name: "Screening assistant" });
  await assistant
    .getByRole("button", { name: "What evidence is missing?", exact: true })
    .click();
  await expect(assistant.locator(".assistant-citation")).toHaveCount(1);
  await assistant.scrollIntoViewIfNeeded();
  await chapter(
    "6. Evidence-only mode is shown here. Published reports test the real OpenAI model.",
  );
  await assistant
    .getByRole("textbox", { name: "Your question" })
    .fill("Enroll this patient now");
  await assistant
    .getByRole("button", { name: "Ask assistant", exact: true })
    .click();
  await expect(assistant).toContainText("I cannot make clinical decisions");
  await chapter(
    "7. The assistant cannot enroll patients or submit review decisions.",
    8,
  );
  await page.getByRole("radio", { name: /Request information/ }).check();
  await page
    .getByRole("textbox", { name: "Reason", exact: true })
    .fill(
      "AUTOMATED DEMONSTRATION: request source clarification; not a human clinical judgment.",
    );
  await page.locator(".review-form").getByRole("checkbox").check();
  await page.locator(".review-form").scrollIntoViewIfNeeded();
  await chapter(
    "8. A reviewer selects the next step and gives a reason. This review is simulated.",
  );
  await page
    .getByRole("button", { name: "Save patient review", exact: true })
    .click();
  await expect(page.locator(".timeline-item")).toContainText(
    "AUTOMATED DEMONSTRATION",
  );
  await page
    .getByRole("navigation")
    .getByRole("button", { name: /Review history/ })
    .click();
  await expect(page.getByRole("table")).toContainText("Information requested");
  await chapter(
    "9. Review history preserves the decision and evidence. No patient is contacted or enrolled.",
  );
  await page
    .getByRole("button", { name: /Open assessment/ })
    .first()
    .click();
  await expect(page.locator(".timeline-item")).toContainText("ui-reviewer");
  await page.locator(".timeline-item").scrollIntoViewIfNeeded();
  await chapter(
    "HealthOps: synthetic records → evidence-backed screening → accountable human review.",
    8,
  );
  expect(errors).toEqual([]);
} finally {
  await context.close();
  await page.video().saveAs(path.join(output, "healthops-demo.webm"));
  await browser.close();
}
