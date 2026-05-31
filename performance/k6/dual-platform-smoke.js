import http from "k6/http";
import { check, group, sleep } from "k6";

const portalBaseUrl = (__ENV.PORTAL_BASE_URL || "https://huairou.tech").replace(/\/$/, "");
const portalAdminBaseUrl = (__ENV.PORTAL_ADMIN_BASE_URL || "https://portal-admin.huairou.tech").replace(/\/$/, "");
const achievementBaseUrl = (__ENV.ACHIEVEMENT_BASE_URL || "https://cg.huairou.tech").replace(/\/$/, "");

const vus = Number.parseInt(__ENV.SMOKE_VUS || "5", 10);
const duration = __ENV.SMOKE_DURATION || "45s";

export const options = {
  vus,
  duration,
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
    checks: ["rate>0.99"],
  },
};

const jsonHeaders = {
  Accept: "application/json",
};

const htmlHeaders = {
  Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
};

function expectStatus(response, allowedStatuses, label) {
  return check(response, {
    [`${label} status`]: (r) => allowedStatuses.includes(r.status),
  });
}

function getJson(url, label) {
  const response = http.get(url, {
    headers: jsonHeaders,
    tags: { platform: label.split(" ")[0], endpoint: label },
  });
  expectStatus(response, [200], label);
  return response;
}

function getHtml(url, label) {
  const response = http.get(url, {
    headers: htmlHeaders,
    tags: { platform: label.split(" ")[0], endpoint: label },
  });
  expectStatus(response, [200], label);
  return response;
}

export default function () {
  group("portal public read-only", () => {
    getHtml(`${portalBaseUrl}/`, "portal home");
    getJson(`${portalBaseUrl}/api/v1/public/home`, "portal public home api");
    getJson(`${portalBaseUrl}/api/v1/public/news?page=1&page_size=5`, "portal public news list");
    getJson(`${portalBaseUrl}/api/v1/public/cases?page=1&page_size=5`, "portal public cases list");
  });

  group("portal admin shell read-only", () => {
    getHtml(`${portalAdminBaseUrl}/`, "portal-admin shell");
  });

  group("achievement public read-only", () => {
    getHtml(`${achievementBaseUrl}/`, "achievement home");
    getJson(`${achievementBaseUrl}/api/v1/health`, "achievement health api");
    getJson(`${achievementBaseUrl}/api/v1/public/achievements?page=1&page_size=10`, "achievement public achievements");
    getJson(`${achievementBaseUrl}/api/v1/public/talents?page=1&page_size=10`, "achievement public talents");
    getJson(`${achievementBaseUrl}/api/v1/public/facilities?page=1&page_size=10`, "achievement public facilities");
  });

  sleep(1 + Math.random() * 2);
}
