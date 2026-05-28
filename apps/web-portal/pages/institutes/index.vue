<script setup lang="ts">
const {
  data,
  pending,
  error,
} = await useAsyncData("institutes", () => usePortalApi<any[]>("/public/institutes"));

useSeoMeta({
  title: "研究所展示",
  description: "研究所模块已接入数据模型，公开范围仍可按确认结果调整。",
});
</script>

<template>
  <div class="container list-page">
    <div class="badge">Reserved / Configurable</div>
    <h1 class="section-title" style="margin-top: 18px;">研究所展示</h1>
    <p class="section-desc">当前页面已接入研究所模型与详情路由，公开深度和固定数量仍可在确认后调整。</p>
    <div v-if="pending" class="card" style="margin-top: 24px; padding: 24px; color: var(--muted);">正在加载研究所信息。</div>
    <div v-else-if="error" class="card" style="margin-top: 24px; padding: 24px; color: #b91c1c;">
      {{ getPortalErrorMessage(error, "研究所信息加载失败") }}
    </div>
    <div v-else-if="!(data || []).length" class="card" style="margin-top: 24px; padding: 24px; color: var(--muted);">
      暂无研究所信息，敬请期待
    </div>
    <div class="card-grid" style="margin-top: 24px;">
      <article v-for="item in data || []" :key="item.slug" class="card" style="grid-column: span 6; padding: 24px;">
        <div class="badge">{{ item.status }}</div>
        <h2 style="font-size: 28px; margin-top: 16px;">
          <NuxtLink :to="`/institutes/${item.slug}`">{{ item.name }}</NuxtLink>
        </h2>
        <p style="color: var(--muted); line-height: 1.8;">{{ item.intro }}</p>
      </article>
    </div>
  </div>
</template>
