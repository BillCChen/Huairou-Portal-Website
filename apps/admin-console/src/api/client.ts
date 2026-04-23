import axios from "axios";

const token = () => localStorage.getItem("portal_admin_token");

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8100/api/v1",
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
