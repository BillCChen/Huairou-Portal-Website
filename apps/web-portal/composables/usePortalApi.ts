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

export const usePortalApi = async <T>(path: string, options: Record<string, unknown> = {}) => {
  const config = useRuntimeConfig();
  const apiBase = resolveApiBase(String(config.public.apiBase || ""));
  const response = await $fetch<{ code: number; message: string; data: T }>(`${apiBase}${path}`, options);
  return response.data;
};
