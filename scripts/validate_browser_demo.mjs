import { spawn } from "node:child_process";
import fs from "node:fs/promises";
import net from "node:net";
import path from "node:path";
import process from "node:process";

import { chromium, devices } from "playwright";

const repoRoot = process.cwd();
const browserPath =
  process.env.PLAYWRIGHT_CHROMIUM_PATH ||
  "/home/helionaut/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome";
const screenshotDir = path.join(repoRoot, ".symphony", "screenshots");
const fixtureA =
  process.env.BROWSER_DEMO_FILE_A ||
  "/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/raw/public-baseline/big-buck-bunny-480p-30sec.mp4";
const fixtureB =
  process.env.BROWSER_DEMO_FILE_B ||
  "/home/helionaut/srv/research-cache/18afd661ce11/datasets/public/raw/public-baseline/big-buck-bunny-1080p-30sec.mp4";

async function ensureFixtures() {
  await fs.access(fixtureA);
  await fs.access(fixtureB);
  await fs.mkdir(screenshotDir, { recursive: true });
}

async function chooseServerPort() {
  if (process.env.BROWSER_DEMO_PORT) {
    return Number(process.env.BROWSER_DEMO_PORT);
  }

  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.on("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      if (!address || typeof address === "string") {
        probe.close(() => reject(new Error("Failed to resolve an ephemeral port.")));
        return;
      }
      probe.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(address.port);
      });
    });
  });
}

function startServer(serverPort) {
  return spawn("python3", ["-m", "http.server", String(serverPort), "--bind", "127.0.0.1"], {
    cwd: repoRoot,
    stdio: "ignore"
  });
}

async function waitForServer(baseUrl) {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch(baseUrl);
      if (response.ok) {
        return;
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`Timed out waiting for ${baseUrl}`);
}

async function runDesktopCheck() {
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1400 } });
  await page.goto(baseUrl);
  await page.setInputFiles("#pair-a", fixtureA);
  await page.setInputFiles("#pair-b", fixtureB);
  await page.click("#load-pair");
  await page.waitForTimeout(2500);

  const badge = await page.textContent("#status-badge");
  const detail = await page.textContent("#status-detail");
  const mode = await page.textContent("#visualization-mode");
  if (!badge?.match(/Analyzing|Ready/)) {
    throw new Error(`Unexpected desktop status badge: ${badge}`);
  }
  if (!detail?.includes("optical-flow approximation")) {
    throw new Error(`Unexpected desktop status detail: ${detail}`);
  }
  if (mode?.trim() !== "optical-flow-approximation") {
    throw new Error(`Unexpected visualization mode: ${mode}`);
  }

  await page.screenshot({
    path: path.join(screenshotDir, "HEL-158-desktop.png"),
    fullPage: true
  });
  await browser.close();
}

async function runMobileCheck() {
  const browser = await chromium.launch({ executablePath: browserPath, headless: true });
  const context = await browser.newContext({ ...devices["iPhone 13"] });
  const page = await context.newPage();
  await page.goto(baseUrl);
  await page.setInputFiles("#pair-a", fixtureA);
  await page.setInputFiles("#pair-b", fixtureB);
  await page.click("#load-pair");
  await page.waitForTimeout(2500);

  const cards = await page.locator(".viewer-card").count();
  if (cards !== 2) {
    throw new Error(`Expected 2 viewer cards on mobile, found ${cards}`);
  }

  await page.screenshot({
    path: path.join(screenshotDir, "HEL-158-mobile.png"),
    fullPage: true
  });
  await browser.close();
}

const serverPort = await chooseServerPort();
const baseUrl = `http://127.0.0.1:${serverPort}/browser-demo/`;
const server = startServer(serverPort);

try {
  await ensureFixtures();
  await waitForServer(baseUrl);
  await runDesktopCheck();
  await runMobileCheck();
  console.log(
    JSON.stringify(
      {
        status: "ok",
        baseUrl,
        screenshots: [
          ".symphony/screenshots/HEL-158-desktop.png",
          ".symphony/screenshots/HEL-158-mobile.png"
        ]
      },
      null,
      2
    )
  );
} finally {
  server.kill("SIGTERM");
}
