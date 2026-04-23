<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
  breadcrumb?: { label: string; to?: string }[];
  sidebarTitle?: string;
  sidebarItems?: { label: string; to: string; query?: Record<string, string> }[];
}>();
</script>

<template>
  <div>
    <SiteHeader />

    <InnerBanner :title="title" :subtitle="subtitle" />

    <div v-if="breadcrumb?.length" class="breadcrumb">
      <div class="container breadcrumb__inner">
        <NuxtLink to="/">首页</NuxtLink>
        <template v-for="(crumb, i) in breadcrumb" :key="i">
          <span class="breadcrumb__sep">/</span>
          <NuxtLink v-if="crumb.to" :to="crumb.to">{{ crumb.label }}</NuxtLink>
          <span v-else class="breadcrumb__current">{{ crumb.label }}</span>
        </template>
      </div>
    </div>

    <div class="inner-page-body">
      <div class="container inner-page-body__wrap">
        <SidebarNav
          v-if="sidebarItems?.length"
          :title="sidebarTitle || title"
          :items="sidebarItems"
        />
        <main class="inner-layout__content">
          <slot />
        </main>
      </div>
    </div>

    <SiteFooter />
  </div>
</template>

<style scoped>
.inner-page-body {
  background: var(--bg-light);
  padding: 32px 0 64px;
}

.inner-page-body__wrap {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}
</style>
