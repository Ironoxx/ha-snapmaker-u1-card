// Source structure guards: mixin method names must be unique (a duplicate would
// silently override another mixin's method), and the bundle must be built from
// the current sources.
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const dir = path.join(__dirname, "../../frontend/src/card");
const seen = new Map();
for (const file of fs.readdirSync(dir)) {
  if (file === "card.js" || file === "mini.js") continue;
  const src = fs.readFileSync(path.join(dir, file), "utf8");
  for (const m of src.matchAll(/^ {2}(?:static |async )?(?:get |set )?([_a-zA-Z0-9]+)\(/gm)) {
    const prev = seen.get(m[1]);
    assert.ok(!prev || prev === file, `method ${m[1]} defined in ${prev} and ${file}`);
    seen.set(m[1], file);
  }
}

const version = /CARD_VERSION = "([^"]+)"/;
const src = fs.readFileSync(path.join(__dirname, "../../frontend/src/const.js"), "utf8").match(version)[1];
const built = fs.readFileSync(path.join(__dirname, "../../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js"), "utf8").match(version)[1];
assert.strictEqual(built, src, "bundle is outdated: run npm run build");
console.log(`STRUCTURE OK – ${seen.size} mixin methods`);
