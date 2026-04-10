import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";

test("browser demo exposes paired frame-by-frame controls and maximum vector detail copy", async () => {
  const html = await fs.readFile("browser-demo/index.html", "utf8");

  assert.match(html, /id="frame-back"/);
  assert.match(html, /id="play-pause"/);
  assert.match(html, /id="frame-forward"/);
  assert.match(html, /Frame-by-frame playback/);
  assert.match(html, /id="vector-detail"/);
});

test("browser demo CSS makes viewer cards full-width and taller", async () => {
  const css = await fs.readFile("browser-demo/app.css", "utf8");

  assert.match(css, /\.viewer-grid\s*{[^}]*grid-template-columns:\s*1fr;/s);
  assert.match(css, /min-height:\s*clamp\(320px,\s*42vw,\s*760px\)/);
});
