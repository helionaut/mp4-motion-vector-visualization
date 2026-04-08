import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";

test("GitHub Pages workflow deploys the browser demo directory from main", async () => {
  const workflow = await fs.readFile(".github/workflows/deploy-pages.yml", "utf8");

  assert.match(workflow, /name:\s+Deploy browser demo to GitHub Pages/);
  assert.match(workflow, /push:\s*\n\s*branches:\s*\n\s*-\s+main/);
  assert.match(workflow, /-\s+"eugeniy\/\*\*"/);
  assert.match(workflow, /uses:\s+actions\/upload-pages-artifact@v3/);
  assert.match(workflow, /path:\s+browser-demo/);
  assert.match(workflow, /if:\s+github\.event\.repository\.private == false && github\.ref == 'refs\/heads\/main'/);
  assert.match(workflow, /uses:\s+actions\/deploy-pages@v4/);
});
