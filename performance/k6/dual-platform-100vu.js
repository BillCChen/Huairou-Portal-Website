import http from "k6/http";
import { check, group, sleep } from "k6";
import { Trend } from "k6/metrics";

const portalBaseUrl = (__ENV.PORTAL_BASE_URL || "https://huairou.tech").replace(/\/$/, "");
const portalAdminBaseUrl = (__ENV.PORTAL_ADMIN_BASE_URL || "https://portal-admin.huairou.tech").replace(/\/$/, "");
const achievementBaseUrl = (__ENV.ACHIEVEMENT_BASE_URL || "https://cg.huairou.tech").replace(/\/$/, "");

const profile = __ENV.PROFILE || "smoke";
const runFullLoad = (__ENV.RUN_FULL_LOAD || "").toLowerCase() === "true";
const allowedProfiles = ["smoke", "warmup10", "baseline50", "diagnose50", "baseline100"];

if (profile === "baseline100" && !runFullLoad) {
  throw new Error("PROFILE=baseline100 requires RUN_FULL_LOAD=true.");
}

if (!allowedProfiles.includes(profile)) {
  throw new Error(`Unsupported PROFILE=${profile}. Use smoke, warmup10, baseline50, diagnose50, or baseline100.`);
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

const diagnose50Options = {
  stages: [
    { duration: __ENV.DIAGNOSE50_RAMP_DURATION || "1m", target: Number.parseInt(__ENV.DIAGNOSE50_VUS || "50", 10) },
    { duration: __ENV.DIAGNOSE50_STEADY_DURATION || "8m", target: Number.parseInt(__ENV.DIAGNOSE50_VUS || "50", 10) },
    { duration: __ENV.DIAGNOSE50_RAMPDOWN_DURATION || "1m", target: 0 },
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
  diagnose50: diagnose50Options,
  baseline100: baseline100Options,
};

export const options = {
  ...profileOptions[profile],
  summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)"],
  thresholds: {
    http_req_failed: ["rate<0.005"],
    "http_req_duration{type:api}": ["p(95)<800"],
    "http_req_duration{type:html}": ["p(95)<1000"],
    endpoint_group_portal_html_duration: ["p(95)<1000"],
    endpoint_group_portal_api_duration: ["p(95)<800"],
    endpoint_group_portal_admin_shell_duration: ["p(95)<1000"],
    endpoint_group_achievement_html_duration: ["p(95)<1000"],
    endpoint_group_achievement_api_duration: ["p(95)<800"],
    http_req_duration: ["p(99)<1500"],
    checks: ["rate>0.99"],
  },
};

const endpointGroupMetrics = {
  portal_html: new Trend("endpoint_group_portal_html_duration", true),
  portal_api: new Trend("endpoint_group_portal_api_duration", true),
  portal_admin_shell: new Trend("endpoint_group_portal_admin_shell_duration", true),
  achievement_html: new Trend("endpoint_group_achievement_html_duration", true),
  achievement_api: new Trend("endpoint_group_achievement_api_duration", true),
};

const endpointMetrics = {
  portal_home_html: new Trend("endpoint_portal_home_html_duration", true),
  portal_public_home_api: new Trend("endpoint_portal_public_home_api_duration", true),
  portal_public_news_api: new Trend("endpoint_portal_public_news_api_duration", true),
  portal_public_cases_api: new Trend("endpoint_portal_public_cases_api_duration", true),
  portal_public_settings_api: new Trend("endpoint_portal_public_settings_api_duration", true),
  portal_admin_shell_html: new Trend("endpoint_portal_admin_shell_html_duration", true),
  achievement_home_html: new Trend("endpoint_achievement_home_html_duration", true),
  achievement_health_api: new Trend("endpoint_achievement_health_api_duration", true),
  achievement_public_achievements_api: new Trend("endpoint_achievement_public_achievements_api_duration", true),
  achievement_public_talents_api: new Trend("endpoint_achievement_public_talents_api_duration", true),
  achievement_public_facilities_api: new Trend("endpoint_achievement_public_facilities_api_duration", true),
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

function recordDuration(response, endpointName, endpointGroup) {
  const duration = response.timings.duration;
  endpointGroupMetrics[endpointGroup].add(duration);
  endpointMetrics[endpointName].add(duration);
}

function requestJson(url, endpointName, endpointGroup, platform) {
  const response = http.get(url, {
    headers: jsonHeaders,
    tags: { name: endpointName, platform, endpoint: endpointName, endpoint_group: endpointGroup, type: "api" },
  });
  recordDuration(response, endpointName, endpointGroup);
  check(response, {
    [`${endpointName} status 200`]: (r) => r.status === 200,
  });
  return response;
}

function requestHtml(url, endpointName, endpointGroup, platform) {
  const response = http.get(url, {
    headers: htmlHeaders,
    tags: { name: endpointName, platform, endpoint: endpointName, endpoint_group: endpointGroup, type: "html" },
  });
  recordDuration(response, endpointName, endpointGroup);
  check(response, {
    [`${endpointName} status 200`]: (r) => r.status === 200,
  });
  return response;
}

const portalPublicFlow = () => {
  group("portal html", () => {
    requestHtml(`${portalBaseUrl}/`, "portal_home_html", "portal_html", "portal");
  });

  group("portal api", () => {
    requestJson(`${portalBaseUrl}/api/v1/public/home`, "portal_public_home_api", "portal_api", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/news?page=1&page_size=5`, "portal_public_news_api", "portal_api", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/cases?page=1&page_size=5`, "portal_public_cases_api", "portal_api", "portal");
    requestJson(`${portalBaseUrl}/api/v1/public/settings`, "portal_public_settings_api", "portal_api", "portal");
  });
};

const achievementPublicFlow = () => {
  group("achievement html", () => {
    requestHtml(`${achievementBaseUrl}/`, "achievement_home_html", "achievement_html", "achievement");
  });

  group("achievement api", () => {
    requestJson(`${achievementBaseUrl}/api/v1/health`, "achievement_health_api", "achievement_api", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/public/achievements?page=1&page_size=10`, "achievement_public_achievements_api", "achievement_api", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/public/talents?page=1&page_size=10`, "achievement_public_talents_api", "achievement_api", "achievement");
    requestJson(`${achievementBaseUrl}/api/v1/public/facilities?page=1&page_size=10`, "achievement_public_facilities_api", "achievement_api", "achievement");
  });
};

const portalAdminShellFlow = () => {
  group("portal admin shell", () => {
    requestHtml(`${portalAdminBaseUrl}/`, "portal_admin_shell_html", "portal_admin_shell", "portal-admin");
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
