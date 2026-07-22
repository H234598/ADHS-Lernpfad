import { test, expect } from "@playwright/test";

function captureBrowserErrors(page) {
  const errors = [];
  page.on("console", (message) => {
    if (message.type() === "error") {
      const location = message.location();
      errors.push(`${message.text()} @ ${location.url || "unknown source"}`);
    }
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

async function visibleNodeIds(page) {
  return page.locator("[data-kg-node-row]:not([hidden])").evaluateAll((rows) =>
    rows.map((row) => row.dataset.nodeId).sort(),
  );
}

function lifecycleStatus(node) {
  if (node.type === "placeholder") return "not_applicable";
  if (["planned", "in_progress", "published"].includes(node.lifecycle_status)) return node.lifecycle_status;
  return node.planned === true ? "planned" : "published";
}

function searchable(node) {
  const status = node.type === "placeholder"
    ? String(node.issue_code || "missing-document")
    : (node.planned === true ? "planned" : String(node.graph_status || node.link_status || "ok"));
  return [node.id, node.label, node.title, node.path, node.type, node.scope, status, lifecycleStatus(node)]
    .concat(Array.isArray(node.aliases) ? node.aliases : [])
    .concat(Array.isArray(node.tags) ? node.tags : [])
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("de");
}

test("Graph, Laufstatus, Suche und Neurobiologie-Filter funktionieren", async ({ page }) => {
  // Material for MkDocs asks GitHub for the latest release to decorate the
  // repository link. This project can legitimately have no release yet, in
  // which case GitHub returns 404 and Chromium emits an unrelated console
  // error. Keep the graph smoke test deterministic and scoped to local assets.
  await page.route(
    "https://api.github.com/repos/H234598/ADHS-Lernpfad/releases/latest",
    (route) => route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ tag_name: "unreleased" }),
    }),
  );
  const errors = captureBrowserErrors(page);
  const response = await page.goto("/knowledge-graph/");
  expect(response?.status()).toBe(200);

  await expect(page.locator("[data-knowledge-graph]")).toBeVisible();
  await expect(page.locator("[data-kg-canvas] canvas").first()).toBeVisible();
  await expect(page.locator("[data-kg-live]")).toContainText(/Knoten sichtbar/);
  await expect(page.locator("[data-kg-runtime-live]")).toContainText(/Generator: OK/);
  await expect(page.getByRole("heading", { name: "Letzter Generatorlauf" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Semantische Graphansicht" })).toBeVisible();
  const graph = await page.evaluate(() => fetch("/knowledge-graph/data/knowledge-graph.json").then((response) => response.json()));
  const allIds = graph.nodes.map((node) => String(node.id)).sort();
  expect(await visibleNodeIds(page)).toEqual(allIds);

  const search = page.locator("[data-kg-search]");
  await search.fill("ADHS");
  const searchedIds = graph.nodes.filter((node) => searchable(node).includes("adhs")).map((node) => String(node.id)).sort();
  expect(searchedIds.length).toBeGreaterThan(0);
  expect(searchedIds.length).toBeLessThan(allIds.length);
  expect(await visibleNodeIds(page)).toEqual(searchedIds);

  await page.locator("[data-kg-reset]").click();
  expect(await visibleNodeIds(page)).toEqual(allIds);
  await page.locator("[data-kg-tag]").selectOption({ label: "Neurobiologie" });
  const taggedIds = graph.nodes.filter((node) => Array.isArray(node.tags) && node.tags.includes("Neurobiologie")).map((node) => String(node.id)).sort();
  expect(taggedIds.length).toBeGreaterThan(0);
  expect(await visibleNodeIds(page)).toEqual(taggedIds);

  await page.locator("[data-kg-reset]").click();
  await page.locator("[data-kg-lifecycle]").selectOption("planned");
  const plannedIds = graph.nodes.filter((node) => lifecycleStatus(node) === "planned").map((node) => String(node.id)).sort();
  expect(plannedIds.length).toBeGreaterThan(0);
  expect(await visibleNodeIds(page)).toEqual(plannedIds);
  await page.locator("[data-kg-reset]").click();
  expect(await visibleNodeIds(page)).toEqual(allIds);
  expect(errors).toEqual([]);
});

test("No-JavaScript-Fallback bleibt sichtbar und navigierbar", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  const response = await page.goto("http://127.0.0.1:8765/knowledge-graph/");
  expect(response?.status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Letzter Generatorlauf" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Semantische Graphansicht" })).toBeVisible();
  await expect(page.locator("table[data-kg-node-table] tbody tr").first()).toBeVisible();
  await expect(page.locator("table[data-kg-edge-table] tbody tr").first()).toBeVisible();
  const link = page.locator("table[data-kg-node-table] tbody a").first();
  await expect(link).toBeVisible();
  const navigation = await Promise.all([page.waitForNavigation(), link.click()]);
  expect(navigation[0]?.status()).toBe(200);
  await context.close();
});

test("Tabelle und Details sind per Tastatur auf Mobilbreite bedienbar", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/knowledge-graph/");
  await expect(page.locator("[data-kg-canvas] canvas").first()).toBeVisible();
  const detailsButton = page.locator(".kg-node-select").first();
  await detailsButton.focus();
  await expect(detailsButton).toBeFocused();
  await detailsButton.press("Enter");
  await expect(page.locator("[data-kg-details] h2")).not.toHaveText("Details");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("Unsichere Backslash-URL wird im Detailpanel nicht verlinkt", async ({ page }) => {
  let maliciousId = "";
  await page.route("**/knowledge-graph/data/knowledge-graph.json", async (route) => {
    const response = await route.fetch();
    const graph = await response.json();
    const target = graph.nodes.find((node) => node.type === "chapter" && node.url);
    maliciousId = String(target.id);
    target.url = "/\\evil.example/";
    await route.fulfill({ response, json: graph });
  });
  await page.goto("/knowledge-graph/");
  await page.locator(`[data-node-id="${maliciousId}"] .kg-node-select`).click();
  await expect(page.locator("[data-kg-details] h2")).not.toHaveText("Details");
  await expect(page.locator('[data-kg-details] a[href*="evil.example"]')).toHaveCount(0);
});
