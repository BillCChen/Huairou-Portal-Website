const localHosts = new Set(["localhost", "127.0.0.1"]);

const resolveApiBase = (apiBase: string) => {
  let resolved = apiBase;

  if (import.meta.client && localHosts.has(window.location.hostname)) {
    try {
      const url = new URL(apiBase);
      if (localHosts.has(url.hostname)) {
        url.hostname = window.location.hostname;
        resolved = url.toString();
      }
    } catch {
      resolved = apiBase;
    }
  }

  return resolved.replace(/\/$/, "");
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readTextField(value: unknown, key: "message" | "detail"): string | undefined {
  if (!isRecord(value)) {
    return undefined;
  }

  const field = value[key];
  return typeof field === "string" && field.trim().length > 0 ? field : undefined;
}

export function getPortalErrorMessage(error: unknown, fallback = "数据加载失败，请稍后重试"): string {
  if (typeof error === "string" && error.trim().length > 0) {
    return error;
  }

  if (!isRecord(error)) {
    return fallback;
  }

  const directMessage = readTextField(error, "message");
  if (directMessage) {
    return directMessage;
  }

  const data = error["data"];
  const dataMessage = readTextField(data, "message") ?? readTextField(data, "detail");
  if (dataMessage) {
    return dataMessage;
  }

  const response = error["response"];
  const responseData = isRecord(response) ? response["_data"] : undefined;
  const responseMessage = readTextField(responseData, "message") ?? readTextField(responseData, "detail");
  if (responseMessage) {
    return responseMessage;
  }

  return fallback;
}

export const isPortalUnauthorizedError = (error: unknown) => {
  if (!isRecord(error)) {
    return false;
  }
  const statusCode = error["statusCode"] ?? error["status"];
  if (statusCode === 401) {
    return true;
  }
  const response = error["response"];
  if (!isRecord(response)) {
    return false;
  }
  return response["status"] === 401 || response["statusCode"] === 401;
};

export const handlePortalAuthExpired = async () => {
  if (!import.meta.client) {
    return;
  }
  clearPortalSession();
  const route = useRoute();
  if (route.path !== "/login") {
    await navigateTo({ path: "/login", query: { reason: "expired" } });
  }
};

export const usePortalApi = async <T>(path: string, options: Record<string, unknown> = {}) => {
  const config = useRuntimeConfig();
  const apiBase = resolveApiBase(String(config.public.apiBase || ""));
  try {
    const response = await $fetch<{ code: number; message: string; data: T }>(`${apiBase}${path}`, options);
    return response.data;
  } catch (error) {
    if (isPortalUnauthorizedError(error)) {
      await handlePortalAuthExpired();
    }
    throw error;
  }
};

export type PortalUser = {
  id: number;
  username?: string | null;
  mobile?: string | null;
  email?: string | null;
  real_name?: string | null;
  organization?: string | null;
  expertise?: string | null;
  status?: string | null;
  role_id?: number | null;
  role_code?: string | null;
  role_name?: string | null;
};

export const passwordPolicyHint = "密码需为 8–20 位，并至少包含大写字母、小写字母、数字、特殊字符中的 3 类。";

export const isPasswordPolicyCompliant = (password: string) => {
  const classes = [
    /[A-Z]/.test(password),
    /[a-z]/.test(password),
    /\d/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ].filter(Boolean).length;
  return password.length >= 8 && password.length <= 20 && classes >= 3;
};

export const getPortalToken = () => {
  if (!import.meta.client) {
    return null;
  }
  return localStorage.getItem("portal_token");
};

export const setPortalSession = (token: string, user: PortalUser) => {
  if (!import.meta.client) {
    return;
  }
  localStorage.setItem("portal_token", token);
  localStorage.setItem("portal_user", JSON.stringify(user));
  window.dispatchEvent(new Event("portal-auth-changed"));
};

export const clearPortalSession = () => {
  if (!import.meta.client) {
    return;
  }
  localStorage.removeItem("portal_token");
  localStorage.removeItem("portal_user");
  window.dispatchEvent(new Event("portal-auth-changed"));
};

export const getCurrentPortalUser = async () => {
  const token = getPortalToken();
  if (!token) {
    return null;
  }
  return usePortalApi<PortalUser>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export type PasswordResetRequestPayload = {
  email_or_username: string;
};

export type PasswordResetConfirmPayload = {
  token: string;
  new_password: string;
};

export const requestPasswordReset = async (emailOrUsername: string) => {
  return usePortalApi<{ message: string }>("/auth/password-reset/request", {
    method: "POST",
    body: {
      email_or_username: emailOrUsername,
    } satisfies PasswordResetRequestPayload,
  });
};

export const confirmPasswordReset = async (token: string, newPassword: string) => {
  return usePortalApi<{ message: string }>("/auth/password-reset/confirm", {
    method: "POST",
    body: {
      token,
      new_password: newPassword,
    } satisfies PasswordResetConfirmPayload,
  });
};
