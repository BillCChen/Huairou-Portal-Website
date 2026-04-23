export const useSiteSettings = () => {
  return useAsyncData("site-settings", () =>
    usePortalApi<Record<string, any>>("/public/settings"),
  );
};
