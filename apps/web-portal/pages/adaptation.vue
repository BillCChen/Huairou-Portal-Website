<script setup lang="ts">
const { data: settings } = await useSiteSettings();

let page: any = null;
try {
  page = await usePortalApi<any>("/public/pages/adaptation");
} catch {
  page = null;
}

const pageTitle = page?.title || "客户端适配";
const pageDescription =
  page?.summary || "面向PC与移动端的展示体验统一配置，聚焦关键路径的跨端可访问性。";
const sectionItems = [
  { title: "响应式设计", detail: "适配PC、平板、手机等终端的结构化布局调整。"},
  { title: "核心功能", detail: "保留重点内容入口与咨询、查询、发布等关键操作在移动端可用。"},
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
        <p>该板块用于配置客户端适配策略与体验说明，支持将现有公开内容同步到不同终端展示。</p>
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
