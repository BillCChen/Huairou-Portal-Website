<script setup lang="ts">
const { data: settings } = await useSiteSettings();

let page: any = null;
try {
  page = await usePortalApi<any>("/public/pages/incubation");
} catch {
  page = null;
}

const pageTitle = page?.title || "成果孵化";
const pageDescription =
  page?.summary || "围绕项目孵化、创业支持和政策支持，构建研究院成果从立项到落地的完整服务链路。";
const sectionItems = [
  { title: "项目孵化", detail: "发布在孵项目、孵化成果和落地企业信息，形成可追踪服务入口。" },
  { title: "创业支持", detail: "提供创业政策解读、资源对接、导师匹配与项目推进指导。" },
  { title: "政策支持", detail: "发布扶持政策、申报指南、政策解读与配套服务公告。" },
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
        <p>该板块用于承接成果孵化相关内容，当前未录入结构化说明，页面已保留模板结构以便后台填充。</p>
      </div>
    </section>

    <section style="margin-top: 24px;">
      <div class="card-grid">
        <article v-for="item in sectionItems" :key="item.title" class="card" style="grid-column: span 4; padding: 22px;">
          <div class="badge">{{ item.title }}</div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 14px;">{{ item.title }}</div>
          <div style="margin-top: 12px; color: var(--muted); line-height: 1.8;">{{ item.detail }}</div>
        </article>
      </div>
    </section>
  </div>
</template>
