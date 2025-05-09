/**
 * test_arthropod_collection_endpoints.js
 * 
 * Hits Arthropod-Collection endpoints with a 2025 date filter,
 * and saves the raw JSON to ./vectorsurv/downloads/arthropod/.
 */

const axios = require("axios");
const fs = require("fs");
const path = require("path");

// Config
const TOKEN_FILE    = "./vectorsurv/response.txt";
const DOWNLOAD_DIR  = "./vectorsurv/downloads/arthropod";
const COLLECTIONS   = "./vectorsurv/downloads/collection_2025.json";
const API_BASE      = "https://api.vectorsurv.org";

// Ensure output folder exists
if (!fs.existsSync(DOWNLOAD_DIR)) fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });

// Load your token
const token = JSON.parse(fs.readFileSync(TOKEN_FILE, "utf8")).token;
const headers = { Authorization: `Bearer ${token}` };

// Date filter params
const dateParams = {
  "query[collection_date][$between][0]": "2025-01-01T00:00:00.000Z",
  "query[collection_date][$between][1]": "2025-05-01T23:59:59.000Z",
};

// Load your collection IDs
let collections = [];
try {
  collections = JSON.parse(fs.readFileSync(COLLECTIONS, "utf8"));
} catch (err) {
  console.error("❌ Could not load collection_2025.json:", err.message);
  process.exit(1);
}

// Endpoint list, with params on the listing endpoints
const endpoints = [
  { 
    url: "/v1/arthropod/collection",      
    file: "collection_list.json",
    params: dateParams
  },
  { 
    url: "/v1/arthropod/abundance/flat",  
    file: "abundance_flat.json",
    params: dateParams
  },
];

// For each collection, add the per-id endpoints (no date filter)
collections.forEach(col => {
  const id = col.id;
  endpoints.push(
    { 
      url: `/v1/arthropod/collection/${id}`,            
      file: `collection_${id}.json`
    },
    { 
      url: `/v1/arthropod/collection/${id}/arthropod`, 
      file: `collection_${id}_arthropods.json`
    }
  );
});

// Helper to save a JSON response
function save(name, data) {
  const out = path.join(DOWNLOAD_DIR, name);
  fs.writeFileSync(out, JSON.stringify(data, null, 2));
  console.log(`✅ Saved ${name}`);
}

async function run() {
  for (const ep of endpoints) {
    const url    = API_BASE + ep.url;
    const config = { headers };
    if (ep.params) config.params = ep.params;

    try {
      const resp = await axios.get(url, config);
      // prefer JSON.rows if paginated
      const data = resp.data.rows || resp.data;
      save(ep.file, data);
    } catch (err) {
      console.error(`❌ Error hitting ${ep.url}:`, err.response?.data || err.message);
    }
  }
}

run();
