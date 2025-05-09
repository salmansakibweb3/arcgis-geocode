/**
 * Enhanced endpoint tester:
 *  - Swaps coords for population-classification
 *  - Tests site-specific land usage
 *  - Tests region by ID
 */

const axios = require("axios");
const fs = require("fs");
const path = require("path");

// Config
const TOKEN_FILE = "./vectorsurv/response.txt";
const DL = "./vectorsurv/downloads";
const OUT_DIR = path.join(DL, "additional");

// Ensure output folder
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

// Read token
const token = JSON.parse(fs.readFileSync(TOKEN_FILE, "utf8")).token;
const headers = { Authorization: `Bearer ${token}` };

// Load your site.json so we can grab a real site ID & coords
let sites = [];
try {
  sites = JSON.parse(fs.readFileSync(path.join(DL, "site.json"), "utf8"));
} catch (e) {
  console.warn("⚠️ Could not load site.json:", e.message);
}

// Base endpoints to test
const endpoints = [
  "/v1/arthropod/collection/",                // all regions
  "/v1/region",                // all regions
  "/v1/region/222",            // specific region (Fresno)
  "/v1/coordinate-precision",  // precision lookup
  "/v1/region/type",           // region types
];

// If we have at least one site, test these
if (sites.length) {
  const s = sites[0];
  // Swap to lat,long for population-classification
  if (s.shape && Array.isArray(s.shape.coordinates)) {
    const [lon, lat] = s.shape.coordinates;
    endpoints.push(`/v1/population-classification/point/${lat},${lon}`);
  }
  // Query land usage for that site ID
  endpoints.push(`/v1/site/land-usage/query/${s.id}`);
}

// Function to turn an endpoint into a safe filename
function fname(ep) {
  return ep
    .replace(/^\/+/, "")      // remove leading slash
    .replace(/[\/?&=\[\],]+/g, "_") // replace unsafe chars
    + ".json";
}

// Fetch & save
async function run() {
  for (const ep of endpoints) {
    const url = `https://api.vectorsurv.org${ep}`;
    try {
      const resp = await axios.get(url, { headers });
      const data = resp.data.rows || resp.data;
      fs.writeFileSync(path.join(OUT_DIR, fname(ep)), JSON.stringify(data, null, 2));
      console.log(`✅ Saved ${ep} → additional/${fname(ep)}`);
    } catch (err) {
      console.error(`❌ Error ${ep}:`, err.response?.data || err.message);
    }
  }
}

run();
