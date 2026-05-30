import axios from "axios";

const token = () => localStorage.getItem("portal_admin_token");
const localHosts = new Set(["localhost", "127.0.0.1"]);
export const ADMIN_AUTH_EXPIRED_EVENT = "portal-admin-auth-expired";

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

export const isAdminUnauthorizedError = (error: unknown) => axios.isAxiosError(error) && error.response?.status === 401;

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isAdminUnauthorizedError(error)) {
      localStorage.removeItem("portal_admin_token");
      window.dispatchEvent(new Event(ADMIN_AUTH_EXPIRED_EVENT));
    }
    return Promise.reject(error);
  },
);

export const unwrap = async <T>(request: Promise<{ data: { data: T } }>) => {
  const response = await request;
  return response.data.data;
};

export const getApiErrorMessage = (error: unknown, fallback = "操作失败") => {
  if (axios.isAxiosError(error)) {
    const message = error.response?.data?.message || error.response?.data?.detail;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return fallback;
};

export type AdminUserCreatePayload = {
  username: string;
  email?: string | null;
  mobile?: string | null;
  real_name: string;
  organization?: string | null;
  expertise?: string | null;
  password: string;
  role_code: string;
};

export type LoginLockoutUnlockPayload = {
  reason: string;
};

export const adminUsersApi = {
  list(params: { page: number; page_size: number; status?: string }) {
    return unwrap<{ items: any[]; total: number; page: number; page_size: number }>(
      api.get("/admin/users", { params }),
    );
  },
  listRoles() {
    return unwrap<Array<{ id: number; code: string; name: string; description?: string }>>(
      api.get("/admin/roles"),
    );
  },
  create(payload: AdminUserCreatePayload) {
    return unwrap<any>(api.post("/admin/users", payload));
  },
  approve(id: number) {
    return unwrap<any>(api.post(`/admin/users/${id}/approve`, { review_comment: "管理员审批通过" }));
  },
  reject(id: number, reason: string) {
    return unwrap<any>(api.post(`/admin/users/${id}/reject`, { reason }));
  },
  disable(id: number) {
    return unwrap<any>(api.post(`/admin/users/${id}/disable`));
  },
  enable(id: number) {
    return unwrap<any>(api.post(`/admin/users/${id}/enable`));
  },
  updateRole(id: number, roleCode: string) {
    return unwrap<any>(api.put(`/admin/users/${id}/role`, { role_code: roleCode }));
  },
};

export const adminLoginLockoutsApi = {
  list(params: {
    page: number;
    page_size: number;
    ip?: string;
    username?: string;
    lockout_type?: string;
    active?: boolean;
  }) {
    return unwrap<{ items: any[]; total: number; page: number; page_size: number }>(
      api.get("/admin/login-lockouts", { params }),
    );
  },
  unlock(id: number, payload: LoginLockoutUnlockPayload) {
    return unwrap<any>(api.post(`/admin/login-lockouts/${id}/unlock`, payload));
  },
};
