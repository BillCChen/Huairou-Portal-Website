export const usePortalApi = async <T>(path: string, options: Record<string, unknown> = {}) => {
  const config = useRuntimeConfig();
  const response = await $fetch<{ code: number; message: string; data: T }>(`${config.public.apiBase}${path}`, options);
  return response.data;
};
