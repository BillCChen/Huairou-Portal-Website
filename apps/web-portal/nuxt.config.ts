export default defineNuxtConfig({
  compatibilityDate: "2026-04-22",
  devtools: { enabled: true },
  css: ["~/assets/css/main.css"],
  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8100/api/v1",
    },
  },
  app: {
    head: {
      title: "北京怀柔科学城生命科学产业创新研究院",
      meta: [
        {
          name: "description",
          content: "聚焦生命科学成果转化与创新协同，服务研究、产业与人才资源对接。",
        },
      ],
    },
  },
});
