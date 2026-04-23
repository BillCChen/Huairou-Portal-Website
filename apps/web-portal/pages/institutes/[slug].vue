<script setup lang="ts">
const route = useRoute();
const slug = computed(() => String(route.params.slug));
const { data } = await useAsyncData(
  () => `institute-${slug.value}`,
  async () => {
    try {
      return await usePortalApi<any>(`/public/institutes/${slug.value}`);
    } catch (error: any) {
      if ((error?.statusCode || error?.status) === 404) {
        throw createError({ statusCode: 404, statusMessage: "Page not found" });
      }
      throw error;
    }
  },
  { watch: [slug] },
);

useSeoMeta({
  title: () => data.value?.name || "研究所详情",
  description: () => data.value?.intro || "研究所详情页面",
});
</script>

<template>
  <div class="container list-page">
    <article class="card" style="padding: 30px;">
      <div class="badge">{{ data?.status }}</div>
      <h1 class="section-title" style="margin-top: 18px;">{{ data?.name }}</h1>
      <p class="section-desc">{{ data?.intro }}</p>
      <div class="card-grid" style="margin-top: 22px;">
        <div v-for="direction in data?.directions || []" :key="direction.title" class="card" style="grid-column: span 6; padding: 22px; background: #f8fbff;">
          <div style="font-size: 24px; font-weight: 700;">{{ direction.title }}</div>
          <div style="margin-top: 12px; color: var(--muted); line-height: 1.8;">{{ direction.summary }}</div>
        </div>
      </div>
    </article>
  </div>
</template>
