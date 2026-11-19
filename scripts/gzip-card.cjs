// 2.4: gzip copy of the card bundle next to it. Home Assistant's static path
// (aiohttp FileResponse) sends it to browsers that accept gzip, so phones and
// tablets download ~260 KB instead of ~900 KB. The bytes may differ between
// zlib versions, so CI does not diff this file; tests/test_resource.py checks
// instead that it unpacks to exactly the bundle next to it.
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const file = path.join(__dirname, "../custom_components/snapmaker_u1_card/frontend/snapmaker-u1-card.js");
const gz = zlib.gzipSync(fs.readFileSync(file), { level: 9 });
fs.writeFileSync(`${file}.gz`, gz);
console.log(`gzip: ${path.basename(file)}.gz ${(gz.length / 1024).toFixed(0)} KB`);
