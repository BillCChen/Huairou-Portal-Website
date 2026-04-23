<script setup lang="ts">
const items = [
  { label: "首页", to: "/" },
  { label: "新闻动态", to: "/news" },
  { label: "成功案例", to: "/cases" },
  { label: "关于我们", to: "/about" },
  { label: "研究所展示", to: "/institutes" },
  { label: "人才服务", to: "/talent" },
  { label: "在线服务", to: "/service" },
];
</script>

<template>
  <header style="position: sticky; top: 0; z-index: 20; backdrop-filter: blur(18px); background: rgba(249, 251, 254, 0.82); border-bottom: 1px solid rgba(217, 227, 240, 0.7);">
    <div class="container" style="display: flex; align-items: center; justify-content: space-between; gap: 16px; min-height: 76px;">
      <NuxtLink to="/" style="display: flex; align-items: center; gap: 12px;">
        <div style="width: 42px; height: 42px; border-radius: 14px; background: linear-gradient(135deg, #0f5b78, #2a7d6f);"></div>
        <div>
          <div style="font-size: 12px; color: var(--muted); letter-spacing: 0.12em;">PORTAL</div>
          <div style="font-size: 18px; font-weight: 700;">生命科学产业创新研究院</div>
        </div>
      </NuxtLink>
      <nav style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap; justify-content: flex-end;">
        <NuxtLink v-for="item in items" :key="item.to" :to="item.to" style="font-size: 14px; color: #314155;">
          {{ item.label }}
        </NuxtLink>
        <NuxtLink to="/login" class="button" style="padding: 10px 16px;">登录</NuxtLink>
      </nav>
    </div>
  </header>
</template>
