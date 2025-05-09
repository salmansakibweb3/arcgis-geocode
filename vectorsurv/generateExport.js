/**
 * Generates a CSV matching the GUI "Export Data" columns
 * by joining your local JSON exports.
 */

const fs = require("fs");
const path = require("path");
const { parse } = require("json2csv");

const DL = "./vectorsurv/downloads";           // folder where you placed your JSONs
const OUT = "./vectorsurv/downloads/gui_export.csv";

// load JSON helpers
function load(name) {
  return JSON.parse(fs.readFileSync(path.join(DL, name), "utf8"));
}

// ISO week helper
function getDiseaseWeek(iso) {
  const d = new Date(iso);
  // source: https://stackoverflow.com/a/6117889/…
  const oneJan = new Date(d.getFullYear(), 0, 1);
  const numberOfDays = Math.floor((d - oneJan) / 86400000);
  return Math.ceil((numberOfDays + oneJan.getDay() + 1) / 7);
}

// 1) load all JSONs
const abundance = load("abundance_flat_2025.json");
const collections = load("collection_2025.json");
const sites = load("site.json");
const traps = load("trap.json");
const speciesList = load("species.json");
const sexList = load("sex.json");

// 2) build lookup maps
const collMap    = Object.fromEntries(collections.map(c => [c.id, c]));
const siteMap    = Object.fromEntries(sites.map(s => [s.id, s]));
const trapMap    = Object.fromEntries(traps.map(t => [t.id, t]));
const speciesMap = Object.fromEntries(speciesList.map(s => [s.id, s.full_name || s.display_name || s.name]));
const sexMap     = Object.fromEntries(sexList.map(s => [s.id, s.name]));

// 3) define the exact column order
const FIELDS = [
  "agency_code",
  "agency_collection_num",
  "collection_id",
  "code","name","street","city","zip","region",
  "site_code","site_name","site_street","site_city","site_zip","site_region",
  "calculated_neighborhood","calculated_neighborhood_distance",
  "calculated_city","calculated_city_distance",
  "calculated_subcounty","calculated_county","calculated_state",
  "longitude","latitude","coordinate_precision","group",
  "identified_by","trap_type","lure",
  "collection_date","disease_week","num_trap","trap_nights","trap_problem",
  "comments","species","add_date","add_user",
  "males","females - mixed","females - gravid"
];

// 4) build CSV rows
const rows = abundance.map(a => {
  const coll = collMap[a.collection] || {};
  const site = siteMap[a.site] || {};
  const trap = trapMap[a.trap] || {};
  const sp   = speciesMap[a.species] || "";
  const sx   = sexMap[a.sex] || "";

  // split counts by sex
  const males         = (sx === "Males" ? a.num_count : 0);
  const femMixed      = (sx === "Females - Mixed" ? a.num_count : 0);
  const femGravid     = (sx === "Females - Gravid" ? a.num_count : 0);

  // coordinates
  const [lng, lat] = (site.shape && site.shape.coordinates) || [null, null];

  return {
    agency_code:            "CNSL",               // hard-code your agency code
    agency_collection_num:  a.collection_num,
    collection_id:          a.collection,
    code:                   site.code || "",
    name:                   site.name || "",
    street:                 site.address_1 || "",
    city:                   site.city || "",
    zip:                    site.postal_code || "",
    region:                 site.region || "",
    site_code:              site.code || "",
    site_name:              site.name || "",
    site_street:            site.address_1 || "",
    site_city:              site.city || "",
    site_zip:               site.postal_code || "",
    site_region:            site.region || "",

    // these GUI-only spatial fields are unavailable: blank for now
    calculated_neighborhood:            "",
    calculated_neighborhood_distance:   "",
    calculated_city:                    "",
    calculated_city_distance:           "",
    calculated_subcounty:               "",
    calculated_county:                  "",
    calculated_state:                   "",

    longitude:              lng,
    latitude:               lat,
    coordinate_precision:   site.coordinate_precision || "",
    group:                  site.group || "",

    identified_by:          a.identified_by || coll.identified_by || "",
    trap_type:              trap.name || "",
    lure:                   trap.lure || "",      // leave blank if unavailable

    collection_date:        a.collection_date,
    disease_week:           getDiseaseWeek(a.collection_date),
    num_trap:               a.num_trap,
    trap_nights:            a.trap_nights,
    trap_problem:           a.trap_problem_bit,
    comments:               a.comments,

    species:                sp,
    add_date:               coll.add_date || "",
    add_user:               a.user,

    males:                  males,
    "females - mixed":      femMixed,
    "females - gravid":     femGravid
  };
});

// 5) write out CSV
const csv = parse(rows, { fields: FIELDS });
fs.writeFileSync(OUT, csv);
console.log(`✅ GUI-style CSV written to ${OUT}`);
