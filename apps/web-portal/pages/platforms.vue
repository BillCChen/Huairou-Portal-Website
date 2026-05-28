<script setup lang="ts">
const { data: settings } = await useSiteSettings();

let page: any = null;
try {
  page = await usePortalApi<any>("/public/pages/platforms");
} catch {
  page = null;
}

const pageTitle = page?.title || "共性平台";
const pageDescription =
  page?.summary || "展示共性技术平台清单与服务能力，支持按平台类型快速导航研究院公共资源。";
const sectionItems = [
  { title: "共性平台列表", detail: "梳理医疗器械、实验动物、合成生物学、制剂等共性平台信息。" },
  { title: "共性平台详情", detail: "展现平台服务内容、团队介绍、合作方式与合作成效。"},
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
        <p>该板块用于展示共性平台承载能力与对外服务目录，当前页面结构已就绪，可接入后台文本更新。</p>
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
