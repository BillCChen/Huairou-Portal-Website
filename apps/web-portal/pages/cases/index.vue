<script setup lang="ts">
const route = useRoute();
const router = useRouter();
const page = computed(() => Number(route.query.page || 1));
const keyword = computed(() => String(route.query.keyword || ""));
const currentCategory = computed(() => String(route.query.category || ""));

const { data: settings } = await useSiteSettings();
const { data: categories } = await useAsyncData(
  "case-categories",
  () => usePortalApi<any[]>("/public/categories", { query: { type: "case" } }),
);
const {
  data,
  pending,
  error,
} = await useAsyncData(
  () => `cases-${page.value}-${keyword.value}-${currentCategory.value}`,
  () => usePortalApi<any>("/public/cases", {
    query: {
      page: page.value,
      keyword: keyword.value || undefined,
      category: currentCategory.value || undefined,
    },
  }),
  { watch: [page, keyword, currentCategory] },
);

useSeoMeta({
  title: () => `成功案例 | ${settings.value?.site_profile?.site_name || "门户网站"}`,
  description: "浏览研究院成果转化与合作案例。",
});

const selectCategory = async (slug = "") => {
  await router.push({
    query: {
      ...route.query,
      page: undefined,
      category: slug || undefined,
    },
  });
};
</script>

<template>
  <div class="container list-page">
    <section class="list-page__hero">
      <div class="badge">Case Library</div>
      <h1 class="section-title" style="margin-top: 18px;">成功案例</h1>
      <p class="section-desc">面向成果转化、平台建设与合作项目的案例展示区，当前采用基础列表和详情结构。</p>
    </section>
    <div class="card" style="padding: 18px;">
      <form method="get" style="display: flex; gap: 12px; flex-wrap: wrap;">
        <input class="input" type="text" name="keyword" placeholder="搜索案例标题或摘要" :value="keyword" style="flex: 1 1 320px;" />
        <input type="hidden" name="category" :value="currentCategory" />
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
    <div v-if="pending" class="card-grid" style="margin-top: 24px;">
      <div v-for="placeholder in 4" :key="placeholder" class="card" style="grid-column: span 6; padding: 24px;">
        <div style="height: 14px; width: 96px; border-radius: 999px; background: #e2e8f0;" />
        <div style="height: 32px; width: 74%; border-radius: 10px; background: #e2e8f0; margin-top: 18px;" />
        <div style="height: 16px; width: 100%; border-radius: 8px; background: #edf2f7; margin-top: 18px;" />
        <div style="height: 16px; width: 84%; border-radius: 8px; background: #edf2f7; margin-top: 12px;" />
      </div>
    </div>
    <div v-else-if="error" class="card" style="margin-top: 24px; padding: 24px; color: #b91c1c;">
      {{ getPortalErrorMessage(error, "案例加载失败") }}
    </div>
    <div v-else-if="!(data?.items || []).length" class="card" style="margin-top: 24px; padding: 24px; color: var(--muted);">
      暂无案例
    </div>
    <div class="card-grid" style="margin-top: 24px;">
      <article v-for="item in data?.items || []" :key="item.slug" class="card" style="grid-column: span 6; padding: 24px;">
        <div class="badge">{{ item.stage || "Case" }}</div>
        <h2 style="font-size: 28px; margin-top: 16px;">
          <NuxtLink :to="`/cases/${item.slug}`">{{ item.title }}</NuxtLink>
        </h2>
        <p style="color: var(--muted); line-height: 1.8;">{{ item.summary }}</p>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; color: var(--muted); font-size: 13px;">
          <span>合作方：{{ item.partner_name || "待维护" }}</span>
          <span>阶段：{{ item.stage || "待维护" }}</span>
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <span v-for="highlight in item.highlights || []" :key="highlight" class="badge">{{ highlight }}</span>
        </div>
      </article>
    </div>
  </div>
</template>
