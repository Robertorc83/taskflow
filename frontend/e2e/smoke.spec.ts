import { expect, test, type Page } from "@playwright/test";

/** SPEC-007 F16: the journey must not log a single console error or warning. */
function trackConsole(page: Page): string[] {
  const messages: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning") messages.push(message.text());
  });
  page.on("pageerror", (error) => messages.push(error.message));
  return messages;
}

test("login → create → filter → complete → delete", async ({ page, isMobile }) => {
  const consoleMessages = trackConsole(page);
  const title = `Smoke test ${Date.now()}`;

  await page.goto("/tasks");
  await expect(page).toHaveURL(/\/login$/);

  await page.getByLabel("Email").fill("alice@example.com");
  await page.getByLabel("Password").fill("Alice123!");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Tasks" })).toBeVisible();

  // Create
  await page.getByRole("link", { name: "New task" }).first().click();
  const dialog = page.getByRole("dialog", { name: "New task" });
  await dialog.getByLabel("Title").fill(title);
  await dialog.getByLabel("Description").fill("Created by Playwright");
  await dialog.getByRole("button", { name: "Create task" }).click();
  await expect(page.getByText("Task created")).toBeVisible();
  const card = page.getByRole("article", { name: title });
  await expect(card).toBeVisible();

  // Filter: pending tasks still include it, completed ones do not.
  if (isMobile) {
    await page.getByRole("button", { name: /Filters/ }).click();
    await page
      .getByRole("dialog", { name: "Filters" })
      .getByLabel("Status")
      .selectOption("completed");
    await page.getByRole("button", { name: "Show results" }).click();
  } else {
    await page.getByLabel("Status").selectOption("completed");
  }
  await expect(page).toHaveURL(/status=completed/);
  await expect(page.getByRole("article", { name: title })).toHaveCount(0);
  await page.goto("/tasks");

  // Complete
  await card.getByRole("button", { name: `Complete ${title}` }).click();
  await expect(card.getByText("Completed")).toBeVisible();

  // Delete
  await card.getByRole("button", { name: `Delete ${title}` }).click();
  await page
    .getByRole("dialog", { name: "Delete task?" })
    .getByRole("button", { name: "Delete task" })
    .click();
  await expect(page.getByRole("article", { name: title })).toHaveCount(0);

  expect(consoleMessages).toEqual([]);
});
