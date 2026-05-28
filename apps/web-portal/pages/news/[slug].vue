<script setup lang="ts">
const route = useRoute();
const slug = computed(() => String(route.params.slug));
const { data } = await useAsyncData(
  () => `news-${slug.value}`,
  async () => {
    try {
      return await usePortalApi<any>(`/public/news/${slug.value}`);
    } catch (error: any) {
      if ((error?.statusCode || error?.status) === 404) {
        throw createError({ statusCode: 404, statusMessage: "Page not found" });
      }
      throw error;
    }
  },
  { watch: [slug] },
);

const article = computed(() => data.value?.article);

useSeoMeta({
  title: () => article.value?.seo_title || article.value?.title || "新闻详情",
  description: () => article.value?.seo_description || article.value?.summary || "研究院新闻详情",
});
</script>

<template>
  <div class="container list-page">
    <article class="card" style="padding: 34px;">
      <div class="badge">{{ article?.category_name || article?.source || "研究院新闻" }}</div>
      <h1 style="font-size: clamp(34px, 5vw, 52px); margin: 18px 0 0;">{{ article?.title }}</h1>
      <div style="display: flex; gap: 18px; flex-wrap: wrap; margin-top: 18px; color: var(--muted);">
        <span>{{ article?.author }}</span>
        <span>{{ article?.source }}</span>
        <span>{{ article?.publish_at?.slice?.(0, 10) }}</span>
      </div>
      <p v-if="article?.summary" style="margin-top: 22px; color: var(--muted); line-height: 1.8; font-size: 16px;">
        {{ article.summary }}
      </p>
      <div class="rich-content" style="margin-top: 28px;" v-html="article?.content_html" />
    </article>

    <section style="margin-top: 28px;">
      <div class="section-title" style="font-size: 28px;">相关推荐</div>
      <div class="card-grid" style="margin-top: 18px;">
        <article v-for="item in data?.related || []" :key="item.slug" class="card" style="grid-column: span 4; padding: 20px;">
          <div class="badge">Related</div>
          <h3 style="font-size: 22px;">{{ item.title }}</h3>
          <p style="color: var(--muted); line-height: 1.7;">{{ item.summary }}</p>
          <NuxtLink :to="`/news/${item.slug}`" class="button secondary">查看详情</NuxtLink>
        </article>
      </div>
    </section>
  </div>
</template>
