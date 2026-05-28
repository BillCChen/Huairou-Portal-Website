import axios from "axios";

const token = () => localStorage.getItem("portal_admin_token");
const localHosts = new Set(["localhost", "127.0.0.1"]);

const resolveApiBase = () => {
  const fallback = "http://localhost:8100/api/v1";
  const configured = import.meta.env.VITE_API_BASE_URL || fallback;

  if (!localHosts.has(window.location.hostname)) {
    return configured;
  }

  try {
    const url = new URL(configured);
    if (localHosts.has(url.hostname)) {
      url.hostname = window.location.hostname;
      return url.toString().replace(/\/$/, "");
    }
  } catch {
    return configured;
  }

  return configured;
};

export const api = axios.create({
  baseURL: resolveApiBase(),
});

api.interceptors.request.use((config) => {
  const currentToken = token();
  if (currentToken) {
    config.headers.Authorization = `Bearer ${currentToken}`;
  }
  return config;
});

export const unwrap = async <T>(request: Promise<{ data: { data: T } }>) => {
  const response = await request;
  return response.data.data;
};
