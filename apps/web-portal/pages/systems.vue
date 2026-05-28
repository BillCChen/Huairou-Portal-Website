<script setup lang="ts">
const { data: settings } = await useSiteSettings();

let page: any = null;
try {
  page = await usePortalApi<any>("/public/pages/systems");
} catch {
  page = null;
}

const pageTitle = page?.title || "业务系统模块";
const pageDescription =
  page?.summary || "承载成果转化对接、培训业务和协同办公等外部系统的入口与信息说明。";
const sectionItems = [
  { title: "成果转化资源对接系统", detail: "提供成果对接、项目流转与合作资源配对说明。"},
  { title: "培训业务系统", detail: "支持第三方系统数据共享与对接流程说明。"},
  { title: "协同办公系统", detail: "支撑协同办公跳转与对接说明，覆盖内部协作场景。"},
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
        <p>该板块用于发布业务系统对接说明及入口管理，默认采用预留位结构，可由单页内容维护文本替换。</p>
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
