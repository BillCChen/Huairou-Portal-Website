<script setup lang="ts">
const { data } = await useAsyncData("talent-page", () => usePortalApi<any>("/public/pages/talent"));
</script>

<template>
  <div class="container list-page">
    <div class="badge">Reserved Module</div>
    <h1 class="section-title" style="margin-top: 18px;">人才服务</h1>
    <p class="section-desc">该模块已作为门户一级入口保留，当前按“信息展示优先、投递流程后置确认”落地。</p>
    <div class="card" style="padding: 28px; margin-top: 24px;">
      <div class="rich-content" v-html="data?.content_html" />
    </div>
  </div>
</template>
