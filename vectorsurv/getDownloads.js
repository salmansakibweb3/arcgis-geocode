const axios = require("axios");
const fs = require("fs");
const path = require("path");

// Config
const tokenPath = "./vectorsurv/response.txt";
const downloadFolder = "./vectorsurv/downloads";
const headers = () => ({
  Authorization: `Bearer ${getToken()}`,
  "Content-Type": "application/json"
});

// Date filter for 2025 season
const collectionParams = {
  "query[collection_date][$between][0]": "2025-01-01T00:00:00.000Z",
  "query[collection_date][$between][1]": "2025-05-01T23:59:59.000Z"
};

// Endpoints to pull
const endpoints = [
  { url: "/v1/arthropod/abundance/flat", file: "abundance_flat_2025.json", params: collectionParams },
  { url: "/v1/arthropod/collection", file: "collection_2025.json", params: collectionParams },
  { url: "/v1/species", file: "species.json" },
  { url: "/v1/sex", file: "sex.json" },
  { url: "/v1/site", file: "site.json" },
  { url: "/v1/trap", file: "trap.json" }
];

// Load token
function getToken() {
  const raw = fs.readFileSync(tokenPath, "utf8");
  return JSON.parse(raw).token;
}

// Save as JSON
function saveJson(fileName, data) {
  const outPath = path.join(downloadFolder, fileName);
  fs.writeFileSync(outPath, JSON.stringify(data, null, 2));
  console.log(`✅ Saved ${fileName}`);
}

// Fetch endpoint
async function fetchAndSave(url, file, params = {}) {
  const fullUrl = `https://api.vectorsurv.org${url}`;
  try {
    const response = await axios.get(fullUrl, {
      headers: headers(),
      params
    });
    const data = response.data.rows || response.data;
    saveJson(file, data);
  } catch (err) {
    console.error(`❌ Failed ${file}:`, err.response?.data || err.message);
  }
}

// Main runner
async function run() {
  if (!fs.existsSync(downloadFolder)) {
    fs.mkdirSync(downloadFolder);
  }

  for (const { url, file, params } of endpoints) {
    await fetchAndSave(url, file, params);
  }

  console.log("🎉 All data pulled and saved to ./downloads/");
}

run();
