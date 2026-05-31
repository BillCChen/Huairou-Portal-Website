import http from "k6/http";
import { check, group, sleep } from "k6";

const portalBaseUrl = (__ENV.PORTAL_BASE_URL || "https://huairou.tech").replace(/\/$/, "");
const portalAdminBaseUrl = (__ENV.PORTAL_ADMIN_BASE_URL || "https://portal-admin.huairou.tech").replace(/\/$/, "");
const achievementBaseUrl = (__ENV.ACHIEVEMENT_BASE_URL || "https://cg.huairou.tech").replace(/\/$/, "");

const profile = __ENV.PROFILE || "smoke";
const runFullLoad = (__ENV.RUN_FULL_LOAD || "").toLowerCase() === "true";
const allowedProfiles = ["smoke", "warmup10", "baseline50", "baseline100"];

if (profile === "baseline100" && !runFullLoad) {
  throw new Error("PROFILE=baseline100 requires RUN_FULL_LOAD=true.");
}

if (!allowedProfiles.includes(profile)) {
  throw new Error(`Unsupported PROFILE=${profile}. Use smoke, warmup10, baseline50, or baseline100.`);
}

const smokeOptions = {
  vus: Number.parseInt(__ENV.SMOKE_VUS || "5", 10),
  duration: __ENV.SMOKE_DURATION || "45s",
};

const warmup10Options = {
  vus: Number.parseInt(__ENV.WARMUP10_VUS || "10", 10),
  duration: __ENV.WARMUP10_DURATION || "4m",
};

const baseline50Options = {
  stages: [
    { duration: __ENV.BASELINE50_RAMP_DURATION || "1m", target: Number.parseInt(__ENV.BASELINE50_VUS || "50", 10) },
    { duration: __ENV.BASELINE50_STEADY_DURATION || "7m", target: Number.parseInt(__ENV.BASELINE50_VUS || "50", 10) },
    { duration: __ENV.BASELINE50_RAMPDOWN_DURATION || "1m", target: 0 },
  ],
};

const baseline100Options = {
  stages: [
    { duration: __ENV.WARMUP_DURATION || "2m", target: 10 },
    { duration: __ENV.RAMP_DURATION || "5m", target: 100 },
    { duration: __ENV.STEADY_DURATION || "20m", target: 100 },
    { duration: __ENV.RAMPDOWN_DURATION || "2m", target: 0 },
  ],
};

const profileOptions = {
  smoke: smokeOptions,
  warmup10: warmup10Options,
  baseline50: baseline50Options,
  baseline100: baseline100Options,
};

export const options = {
  ...profileOptions[profile],
  thresholds: {
    http_req_failed: ["rate<0.005"],
    "http_req_duration{type:api}": ["p(95)<800"],
    "http_req_duration{type:html}": ["p(95)<1000"],
    http_req_duration: ["p(99)<1500"],
    checks: ["rate>0.99"],
  },
};

const jsonHeaders = {
  Accept: "application/json",
};

const htmlHeaders = {
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
};

function randomItem(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function requestJson(url, label, platform) {
  const response = http.get(url, {
    headers: jsonHeaders,
    tags: { platform, endpoint: label, type: "api" },
  });
  check(response, {
    [`${label} status 200`]: (r) => r.status === 200,
  });
  return response;
}

function requestHtml(url, label, platform) {
  const response = http.get(url, {
    headers: htmlHeaders,
    tags: { platform, endpoint: label, type: "html" },
  });
  check(response, {
    [`${label} status 200`]: (r) => r.status === 200,
  });
  return response;
}

const portalPublicFlow = () => {
  group("portal public browsing", () => {
    requestHtml(`${portalBaseUrl}/`, "portal home", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/home`, "portal public home api", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/news?page=1&page_size=5`, "portal public news list", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/cases?page=1&page_size=5`, "portal public cases list", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/settings`, "portal public settings", "portal");
  });
};

const achievementPublicFlow = () => {
  group("achievement public browsing", () => {
    requestHtml(`${achievementBaseUrl}/`, "achievement home", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/health`, "achievement health api", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/public/achievements?page=1&page_size=10`, "achievement public achievements", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/public/talents?page=1&page_size=10`, "achievement public talents", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/public/facilities?page=1&page_size=10`, "achievement public facilities", "achievement");
  });
};

const portalAdminShellFlow = () => {
  group("portal admin shell", () => {
    requestHtml(`${portalAdminBaseUrl}/`, "portal-admin shell", "portal-admin");
  });
};

const thinkTime = () => {
  sleep(1 + Math.random() * 2);
};

export default function () {
  const flow = randomItem([
    portalPublicFlow,
    portalPublicFlow,
    portalPublicFlow,
    portalPublicFlow,
    achievementPublicFlow,
    achievementPublicFlow,
    achievementPublicFlow,
    achievementPublicFlow,
    portalAdminShellFlow,
    thinkTime,
  ]);

  flow();
  thinkTime();
}
