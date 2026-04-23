<script setup lang="ts">
const route = useRoute();

const props = defineProps<{
  title: string;
  items: { label: string; to: string; query?: Record<string, string> }[];
}>();

const isActive = (item: { to: string; query?: Record<string, string> }) => {
  if (route.path !== item.to) return false;
  if (!item.query) return true;
  return Object.entries(item.query).every(
    ([k, v]) => route.query[k] === v
  );
};
</script>

<template>
  <aside class="sidebar-nav">
    <div class="sidebar-nav__header">{{ title }}</div>
    <nav class="sidebar-nav__list">
      <NuxtLink
        v-for="item in items"
        :key="item.to + JSON.stringify(item.query)"
        :to="item.query ? { path: item.to, query: item.query } : item.to"
        class="sidebar-nav__item"
        :class="{ 'is-active': isActive(item) }"
      >
        <span class="sidebar-nav__marker" />
        {{ item.label }}
      </NuxtLink>
    </nav>
  </aside>
</template>

<style scoped>
.sidebar-nav {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-white);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  align-self: flex-start;
  position: sticky;
  top: 80px;
}

.sidebar-nav__header {
  background: var(--primary);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  padding: 14px 18px;
  letter-spacing: 0.03em;
}

.sidebar-nav__list {
  display: flex;
  flex-direction: column;
}

.sidebar-nav__item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 18px;
  font-size: 14px;
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px solid var(--border);
  transition: background 0.12s, color 0.12s;
}

.sidebar-nav__item:last-child {
  border-bottom: none;
}

.sidebar-nav__item:hover {
  background: var(--bg-light);
  color: var(--primary);
}

.sidebar-nav__item.is-active {
  background: rgba(10, 78, 168, 0.06);
  color: var(--primary);
  font-weight: 600;
  border-left: 3px solid var(--primary);
  padding-left: 15px;
}

.sidebar-nav__marker {
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.4;
  flex-shrink: 0;
}

.sidebar-nav__item.is-active .sidebar-nav__marker {
  opacity: 1;
}
</style>
