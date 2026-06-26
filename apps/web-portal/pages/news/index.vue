<script setup lang="ts">
definePageMeta({ layout: false });

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
const { data, pending, error } = await useAsyncData(
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
  description: "浏览研究院院内动态、活动与沙龙、科普教育和媒体聚焦。",
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

const sidebarItems = computed(() => [
  { label: "全部新闻", to: "/news" },
  ...((categories.value || []).map((c: any) => ({
    label: c.name,
    to: "/news",
    query: { category_slug: c.slug },
  }))),
]);
</script>

<template>
  <NuxtLayout
    name="inner"
    title="新闻动态"
    subtitle="院内动态、活动与沙龙、科普教育与媒体聚焦统一发布入口"
    :breadcrumb="[{ label: '新闻动态' }]"
    sidebar-title="新闻分类"
    :sidebar-items="sidebarItems"
  >
    <div>
      <div class="news-search">
        <form method="get" style="display: flex; gap: 10px; flex-wrap: wrap;">
          <input
            class="input"
            type="text"
            name="keyword"
            placeholder="搜索新闻标题或摘要"
            :value="keyword"
            style="flex: 1 1 260px;"
          />
          <input type="hidden" name="category_slug" :value="currentCategory" />
          <button class="button" type="submit">搜索</button>
        </form>
      </div>

      <div v-if="pending" style="display: grid; gap: 14px; margin-top: 20px;">
        <div v-for="n in 3" :key="n" class="news-item news-item--skeleton">
          <div class="skeleton skeleton--title" />
          <div class="skeleton skeleton--line" />
          <div class="skeleton skeleton--line skeleton--short" />
        </div>
      </div>

      <div v-else-if="error" class="news-error">
        {{ getPortalErrorMessage(error, "新闻加载失败") }}
      </div>

      <div v-else-if="!(data?.items || []).length" class="news-empty">
        暂无新闻
      </div>

      <div v-else style="display: grid; gap: 0; margin-top: 20px; border-top: 2px solid var(--primary);">
        <article
          v-for="item in data?.items || []"
          :key="item.slug"
          class="news-item"
        >
          <div class="news-item__badges">
            <span class="news-item__source">{{ item.source || "研究院资讯" }}</span>
            <span v-if="item.is_top" class="news-item__top">置顶</span>
          </div>
          <h2 class="news-item__title">
            <NuxtLink :to="`/news/${item.slug}`">{{ item.title }}</NuxtLink>
          </h2>
          <p class="news-item__summary">{{ item.summary }}</p>
          <div class="news-item__meta">
            <span>{{ item.publish_at?.slice?.(0, 10) || "" }}</span>
          </div>
        </article>
      </div>

      <div v-if="data?.total_pages > 1" class="pagination">
        <button
          class="button secondary"
          :disabled="page <= 1"
          @click="router.push({ query: { ...route.query, page: page - 1 } })"
        >
          上一页
        </button>
        <span class="pagination__info">第 {{ page }} / {{ data.total_pages }} 页</span>
        <button
          class="button secondary"
          :disabled="page >= data.total_pages"
          @click="router.push({ query: { ...route.query, page: page + 1 } })"
        >
          下一页
        </button>
      </div>
    </div>
  </NuxtLayout>
</template>

<style scoped>
.news-search {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}

.news-item {
  padding: 20px 0;
  border-bottom: 1px solid var(--border);
}

.news-item__badges {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.news-item__source {
  font-size: 12px;
  color: var(--primary);
  background: rgba(10, 78, 168, 0.08);
  padding: 2px 8px;
  border-radius: 2px;
}

.news-item__top {
  font-size: 11px;
  font-weight: 700;
  background: #dc2626;
  color: #fff;
  padding: 2px 8px;
  border-radius: 2px;
}

.news-item__title {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 8px;
  line-height: 1.45;
}

.news-item__title a {
  color: var(--text);
  text-decoration: none;
  transition: color 0.15s;
}

.news-item__title a:hover {
  color: var(--primary);
}

.news-item__summary {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
  margin: 0 0 10px;
}

.news-item__meta {
  font-size: 12px;
  color: var(--muted);
}

.news-item--skeleton {
  pointer-events: none;
}

.skeleton {
  border-radius: 2px;
  background: #e8eef6;
  animation: shimmer 1.2s infinite;
}

.skeleton--title {
  height: 20px;
  width: 70%;
  margin-bottom: 10px;
}

.skeleton--line {
  height: 14px;
  width: 100%;
  margin-bottom: 8px;
}

.skeleton--short {
  width: 50%;
}

@keyframes shimmer {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.news-error {
  margin-top: 20px;
  padding: 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 4px;
  color: #b91c1c;
  font-size: 14px;
}

.news-empty {
  margin-top: 20px;
  padding: 32px 16px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
  border: 1px dashed var(--border);
  border-radius: 4px;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 28px;
  justify-content: center;
}

.pagination__info {
  font-size: 13px;
  color: var(--muted);
}
</style>
