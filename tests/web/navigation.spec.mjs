import { test, expect } from "@playwright/test";

async function learningCategory(page, title) {
  const label = page.locator(
    ".md-sidebar--primary label.md-nav__link",
    { hasText: title },
  ).first();
  await expect(label).toBeVisible();

  const item = label.locator("xpath=parent::li");
  const nestedNavigation = item.locator(":scope > nav.md-nav");
  return { label, nestedNavigation };
}

test("Lernkategorien sind beim Einstieg geschlossen und gezielt aufklappbar", async ({ page }) => {
  const response = await page.goto("/");
  expect(response?.status()).toBe(200);

  const foundations = await learningCategory(page, "Grundlagen");
  const advanced = await learningCategory(page, "Vertiefung");

  await expect(foundations.nestedNavigation).toBeHidden();
  await expect(advanced.nestedNavigation).toBeHidden();

  await foundations.label.click();
  await expect(foundations.nestedNavigation).toBeVisible();
  await expect(advanced.nestedNavigation).toBeHidden();
});

test("Ein Direktlink öffnet nur die Kategorie der aktiven Lernkarte", async ({ page }) => {
  let response = await page.goto("/01-Grundlagen/01-Was-ist-ADHS/");
  expect(response?.status()).toBe(200);

  let foundations = await learningCategory(page, "Grundlagen");
  let advanced = await learningCategory(page, "Vertiefung");
  await expect(foundations.nestedNavigation).toBeVisible();
  await expect(advanced.nestedNavigation).toBeHidden();
  await expect(
    page.locator(".md-sidebar--primary a.md-nav__link--active", {
      hasText: "Was ist ADHS?",
    }),
  ).toBeVisible();

  response = await page.goto(
    "/02-Vertiefung/01-Pharmakologie-und-Psychotherapie/",
  );
  expect(response?.status()).toBe(200);

  foundations = await learningCategory(page, "Grundlagen");
  advanced = await learningCategory(page, "Vertiefung");
  await expect(foundations.nestedNavigation).toBeHidden();
  await expect(advanced.nestedNavigation).toBeVisible();
  await expect(
    page.locator(".md-sidebar--primary a.md-nav__link--active", {
      hasText: "Pharmakologie und Psychotherapie",
    }),
  ).toBeVisible();
});
