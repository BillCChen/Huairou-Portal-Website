<script setup lang="ts">
const route = useRoute();
const slug = computed(() => String(route.params.slug));
const { data } = await useAsyncData(
  () => `case-${slug.value}`,
  async () => {
    try {
      return await usePortalApi<any>(`/public/cases/${slug.value}`);
    } catch (error: any) {
      if ((error?.statusCode || error?.status) === 404) {
        throw createError({ statusCode: 404, statusMessage: "Page not found" });
      }
      throw error;
    }
  },
  { watch: [slug] },
);

const caseItem = computed(() => data.value?.case);

useSeoMeta({
  title: () => caseItem.value?.seo_title || caseItem.value?.title || "案例详情",
  description: () => caseItem.value?.seo_description || caseItem.value?.summary || "成果转化案例详情",
});
</script>

<template>
  <div class="container list-page">
    <article class="card" style="padding: 34px;">
      <div class="badge">{{ caseItem?.stage || "Case" }}</div>
      <h1 style="font-size: clamp(34px, 5vw, 52px); margin: 18px 0 0;">{{ caseItem?.title }}</h1>
      <div style="display: flex; gap: 18px; flex-wrap: wrap; margin-top: 18px; color: var(--muted);">
        <span>合作方：{{ caseItem?.partner_name || "待确认" }}</span>
        <span>{{ caseItem?.publish_at?.slice?.(0, 10) }}</span>
      </div>
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px;">
        <span v-for="highlight in caseItem?.highlights || []" :key="highlight" class="badge">{{ highlight }}</span>
      </div>
      <div class="rich-content" style="margin-top: 28px;" v-html="caseItem?.content_html" />
      <div v-if="caseItem?.benefits" class="card" style="margin-top: 24px; padding: 22px; background: #f8fbff;">
        <div style="font-size: 20px; font-weight: 700;">成果成效</div>
        <div style="margin-top: 12px; color: var(--muted); line-height: 1.8;">{{ caseItem.benefits }}</div>
      </div>
    </article>

    <section style="margin-top: 28px;">
      <div class="section-title" style="font-size: 28px;">相关推荐</div>
      <div class="card-grid" style="margin-top: 18px;">
        <article v-for="item in data?.related || []" :key="item.slug" class="card" style="grid-column: span 4; padding: 20px;">
          <div class="badge">Related</div>
          <h3 style="font-size: 22px;">{{ item.title }}</h3>
          <p style="color: var(--muted); line-height: 1.7;">{{ item.summary }}</p>
          <NuxtLink :to="`/cases/${item.slug}`" class="button secondary">查看详情</NuxtLink>
        </article>
      </div>
    </section>
  </div>
</template>
