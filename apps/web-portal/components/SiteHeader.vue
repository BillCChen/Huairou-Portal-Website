<script setup lang="ts">
const route = useRoute();
const items = [
  { label: "首页", to: "/" },
  { label: "新闻动态", to: "/news" },
  { label: "成功案例", to: "/cases" },
  { label: "关于我们", to: "/about" },
  { label: "研究所展示", to: "/institutes" },
  { label: "人才服务", to: "/talent" },
  { label: "在线服务", to: "/service" },
];
const isActive = (to: string) =>
  to === "/" ? route.path === "/" : route.path.startsWith(to);
</script>

<template>
  <header class="site-header">
    <div class="container site-header__inner">
      <NuxtLink to="/" class="site-header__logo">
        <div class="site-header__logo-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="12" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/>
            <circle cx="14" cy="14" r="6" fill="rgba(255,255,255,0.9)"/>
          </svg>
        </div>
        <div class="site-header__logo-text">
          <span class="site-header__logo-en">LIFE SCIENCE INSTITUTE</span>
          <span class="site-header__logo-cn">生命科学产业创新研究院</span>
        </div>
      </NuxtLink>

      <nav class="site-header__nav">
        <NuxtLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="site-header__nav-item"
          :class="{ 'is-active': isActive(item.to) }"
        >
          {{ item.label }}
        </NuxtLink>
        <NuxtLink to="/login" class="site-header__login">登录</NuxtLink>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--primary-dark);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.site-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
}

.site-header__logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex-shrink: 0;
}

.site-header__logo-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.site-header__logo-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.site-header__logo-en {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.1em;
  line-height: 1;
}

.site-header__logo-cn {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  letter-spacing: 0.02em;
}

.site-header__nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.site-header__nav-item {
  padding: 6px 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.82);
  text-decoration: none;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  line-height: 36px;
}

.site-header__nav-item:hover {
  color: #fff;
}

.site-header__nav-item.is-active {
  color: #fff;
  border-bottom-color: #fff;
  font-weight: 600;
}

.site-header__login {
  margin-left: 8px;
  padding: 7px 18px;
  font-size: 13px;
  color: var(--primary-dark);
  background: #fff;
  border-radius: 2px;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s;
}

.site-header__login:hover {
  background: #e8eef8;
}
</style>
