<script setup lang="ts">
const { data: settings } = await useSiteSettings();

let page: any = null;
try {
  page = await usePortalApi<any>("/public/pages/search-stats");
} catch {
  page = null;
}

const pageTitle = page?.title || "搜索与数据统计";
const pageDescription =
  page?.summary || "面向全站内容检索与访问分析的服务入口，兼顾热门推荐与业务数据洞察。";
const sectionItems = [
  { title: "智能搜索", detail: "覆盖成果、专家、机构与新闻内容的全站检索能力。" },
  { title: "高级筛选", detail: "支持多维度条件筛选，提升精确查找效率。"},
  { title: "访问统计", detail: "汇总访问信息、趋势与访问行为数据。"},
  { title: "业务统计", detail: "支持成果转化与合作对接的业务数据展示。"},
  { title: "智能推荐", detail: "按用户行为与偏好聚合相关内容入口。"},
  { title: "热门内容", detail: "动态展示热度较高的新闻、成果与活动信息。"},
];

useSeoMeta({
  title: () => `${pageTitle} | ${settings.value?.site_profile?.site_name || "门户网站"}`,
  description: () => pageDescription,
});
</script>

<template>
  <div class="container list-page">
    <section class="list-page__hero">
      <div class="badge">Reserved Module</div>
      <h1 class="section-title" style="margin-top: 18px;">{{ pageTitle }}</h1>
      <p class="section-desc">{{ pageDescription }}</p>
    </section>

    <section class="card" style="padding: 28px; margin-top: 24px;">
      <div v-if="page?.content_html" class="rich-content" v-html="page.content_html" />
      <div v-else class="rich-content">
        <p>该板块用于承载搜索能力与数据统计的展示内容，当前已完成页面结构并可接入正式后台文案与指标。 </p>
      </div>
    </section>

    <section style="margin-top: 24px;">
      <div class="card-grid">
        <article v-for="item in sectionItems" :key="item.title" class="card" style="grid-column: span 6; padding: 22px;">
          <div class="badge">{{ item.title }}</div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 14px;">{{ item.title }}</div>
          <div style="margin-top: 12px; color: var(--muted); line-height: 1.8;">{{ item.detail }}</div>
        </article>
      </div>
    </section>
  </div>
</template>
