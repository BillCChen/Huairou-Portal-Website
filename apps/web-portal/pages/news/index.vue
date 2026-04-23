<script setup lang="ts">
const route = useRoute();
const router = useRouter();
const page = computed(() => Number(route.query.page || 1));
const keyword = computed(() => String(route.query.keyword || ""));
const currentCategory = computed(() => String(route.query.category_slug || ""));

const { data: settings } = await useSiteSettings();
const { data: categories } = await useAsyncData(
  "news-categories",
  () => usePortalApi<any[]>("/public/categories", { query: { type: "news" } }),
);
const {
  data,
  pending,
  error,
} = await useAsyncData(
  () => `news-${page.value}-${keyword.value}-${currentCategory.value}`,
  () => usePortalApi<any>("/public/news", {
    query: {
      page: page.value,
      keyword: keyword.value || undefined,
      category: currentCategory.value || undefined,
    },
  }),
  { watch: [page, keyword, currentCategory] },
);

useSeoMeta({
  title: () => `新闻动态 | ${settings.value?.site_profile?.site_name || "门户网站"}`,
  description: "浏览研究院新闻、通知公告和行业资讯。",
});

const selectCategory = async (slug = "") => {
  await router.push({
    query: {
      ...route.query,
      page: undefined,
      category_slug: slug || undefined,
    },
  });
};
</script>

<template>
  <div class="container list-page">
    <section class="list-page__hero">
      <div class="badge">News Center</div>
      <h1 class="section-title" style="margin-top: 18px;">新闻动态</h1>
      <p class="section-desc">统一承接研究院新闻、通知公告与行业资讯，当前提供关键词搜索与分页浏览。</p>
    </section>
    <div class="card" style="padding: 18px;">
      <form method="get" style="display: flex; gap: 12px; flex-wrap: wrap;">
        <input class="input" type="text" name="keyword" placeholder="搜索新闻标题或摘要" :value="keyword" style="flex: 1 1 320px;" />
        <input type="hidden" name="category_slug" :value="currentCategory" />
        <button class="button" type="submit">搜索</button>
      </form>
    </div>
    <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-top: 20px;">
      <button class="button" :class="{ secondary: currentCategory !== '' }" @click="selectCategory()">全部</button>
      <button
        v-for="item in categories || []"
        :key="item.id"
        class="button"
        :class="{ secondary: currentCategory !== item.slug }"
        @click="selectCategory(item.slug)"
      >
        {{ item.name }}
      </button>
    </div>
    <div v-if="pending" style="display: grid; gap: 18px; margin-top: 24px;">
      <div v-for="placeholder in 3" :key="placeholder" class="card" style="padding: 24px;">
        <div style="height: 14px; width: 96px; border-radius: 999px; background: #e2e8f0;" />
        <div style="height: 32px; width: 70%; border-radius: 10px; background: #e2e8f0; margin-top: 18px;" />
        <div style="height: 16px; width: 100%; border-radius: 8px; background: #edf2f7; margin-top: 18px;" />
        <div style="height: 16px; width: 82%; border-radius: 8px; background: #edf2f7; margin-top: 12px;" />
      </div>
    </div>
    <div v-else-if="error" class="card" style="margin-top: 24px; padding: 24px; color: #b91c1c;">
      {{ error.data?.message || error.data?.detail || error.message || "新闻加载失败" }}
    </div>
    <div v-else-if="!(data?.items || []).length" class="card" style="margin-top: 24px; padding: 24px; color: var(--muted);">
      暂无新闻
    </div>
    <div style="display: grid; gap: 18px; margin-top: 24px;">
      <article v-for="item in data?.items || []" :key="item.slug" class="card" style="padding: 24px;">
        <div style="display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap;">
          <div>
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <div class="badge">{{ item.source || "研究院资讯" }}</div>
              <span v-if="item.is_top" style="display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; background: #dc2626; color: #fff; font-size: 12px; font-weight: 700;">置顶</span>
            </div>
            <h2 style="font-size: 28px; margin: 16px 0 0;">
              <NuxtLink :to="`/news/${item.slug}`">{{ item.title }}</NuxtLink>
            </h2>
          </div>
          <div style="color: var(--muted);">{{ item.publish_at?.slice?.(0, 10) || "" }}</div>
        </div>
        <p style="color: var(--muted); line-height: 1.8;">{{ item.summary }}</p>
      </article>
    </div>
  </div>
</template>
