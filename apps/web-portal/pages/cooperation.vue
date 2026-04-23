<script setup lang="ts">
const { data } = await useAsyncData("cooperation-page", () => usePortalApi<any>("/public/pages/cooperation"));
</script>

<template>
  <div class="container list-page">
    <div class="badge">Reserved Module</div>
    <h1 class="section-title" style="margin-top: 18px;">产学研合作</h1>
    <p class="section-desc">该页面已预留为正式导航和后续活动报名、合作项目展示的承载位，报名闭环仍待确认。</p>
    <div class="card" style="padding: 28px; margin-top: 24px;">
      <div class="rich-content" v-html="data?.content_html" />
    </div>
  </div>
</template>
