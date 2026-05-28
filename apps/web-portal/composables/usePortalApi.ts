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

export const usePortalApi = async <T>(path: string, options: Record<string, unknown> = {}) => {
  const config = useRuntimeConfig();
  const apiBase = resolveApiBase(String(config.public.apiBase || ""));
  const response = await $fetch<{ code: number; message: string; data: T }>(`${apiBase}${path}`, options);
  return response.data;
};
