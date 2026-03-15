import { After, AfterAll, Before, BeforeAll, Given, Then, When, setDefaultTimeout, setWorldConstructor } from '@cucumber/cucumber';
import { chromium, Browser, Page } from '@playwright/test';

class SpringstackWorld {
  browser: Browser | null = null;
  page: Page | null = null;
  corpusId: string | null = null;
  itemId: string | null = null;
  corpusSegment: string | null = null;
  itemSegment: string | null = null;
}

setWorldConstructor(SpringstackWorld);

const baseUrl = process.env.E2E_BASE_URL || 'http://localhost:5173';

setDefaultTimeout(60_000);

BeforeAll(async function () {
  const world = this as SpringstackWorld;
  world.browser = await chromium.launch();
});

AfterAll(async function () {
  const world = this as SpringstackWorld;
  if (world.browser) {
    await world.browser.close();
  }
});

Before(async function () {
  const world = this as SpringstackWorld;
  if (!world.browser) {
    world.browser = await chromium.launch();
  }
  world.page = await world.browser.newPage();
});

After(async function () {
  const world = this as SpringstackWorld;
  if (world.page) {
    await world.page.close();
  }
  world.page = null;
});

Given('the explorer is open', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  await world.page.goto(baseUrl, { waitUntil: 'domcontentloaded' });
  await world.page.waitForSelector('[data-crumb-target="root:root"]');
});

When('I open the first corpus', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  const firstCorpus = world.page.locator('[data-item-type="corpus"]').first();
  world.corpusId = await firstCorpus.getAttribute('data-item-id');
  if (!world.corpusId) throw new Error('Missing corpus id');
  await firstCorpus.click();
  await world.page.waitForURL('**/corpus/**');
  const url = new URL(world.page.url());
  const parts = url.pathname.split('/').filter(Boolean);
  world.corpusSegment = parts[1] ?? null;
});

When('I open the first item', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  const firstItem = world.page.locator('[data-item-type="item"]').first();
  world.itemId = await firstItem.getAttribute('data-item-id');
  if (!world.itemId) throw new Error('Missing item id');
  await firstItem.click();
  await world.page.waitForURL('**/item/**');
  const url = new URL(world.page.url());
  const parts = url.pathname.split('/').filter(Boolean);
  world.itemSegment = parts[3] ?? null;
});

When('I click the root breadcrumb', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  await world.page.locator('[data-crumb-target="root:root"]').click();
});

When('I capture the first corpus and item ids', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  const firstCorpus = world.page.locator('[data-item-type="corpus"]').first();
  world.corpusId = await firstCorpus.getAttribute('data-item-id');
  if (!world.corpusId) throw new Error('Missing corpus id');
  await firstCorpus.click();
  await world.page.waitForURL('**/corpus/**');
  const corpusUrl = new URL(world.page.url());
  const corpusParts = corpusUrl.pathname.split('/').filter(Boolean);
  world.corpusSegment = corpusParts[1] ?? null;
  const firstItem = world.page.locator('[data-item-type="item"]').first();
  world.itemId = await firstItem.getAttribute('data-item-id');
  if (!world.itemId) throw new Error('Missing item id');
  await firstItem.click();
  await world.page.waitForURL('**/item/**');
  const itemUrl = new URL(world.page.url());
  const itemParts = itemUrl.pathname.split('/').filter(Boolean);
  world.itemSegment = itemParts[3] ?? null;
});

When('I visit the item deep link', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  if (!world.corpusSegment || !world.itemSegment) throw new Error('Missing segments');
  const path = `/corpus/${world.corpusSegment}/item/${world.itemSegment}`;
  await world.page.goto(`${baseUrl}${path}`, { waitUntil: 'domcontentloaded' });
});

When('I toggle the data mode', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  const toggle = world.page.getByRole('switch');
  await toggle.click();
});

Then('the URL includes the corpus', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  if (!world.corpusSegment) throw new Error('Missing corpus segment');
  await world.page.waitForURL(`**/corpus/${world.corpusSegment}`);
});

Then('the URL includes the item', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  if (!world.corpusSegment || !world.itemSegment) throw new Error('Missing segments');
  await world.page.waitForURL(
    `**/corpus/${world.corpusSegment}/item/${world.itemSegment}`
  );
});

Then('I should be at the root level', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  await world.page.waitForURL('**/');
  await world.page.waitForSelector('[data-item-type="corpus"]');
});

Then('the root breadcrumb label changes', async function () {
  const world = this as SpringstackWorld;
  if (!world.page) throw new Error('No page available');
  const rootCrumb = world.page.locator('[data-crumb-target="root:root"]');
  await rootCrumb.waitFor();
  const text = await rootCrumb.textContent();
  if (!text || (!text.includes('Local') && !text.includes('Cloud'))) {
    throw new Error('Root breadcrumb label did not update to Local/Cloud');
  }
});
