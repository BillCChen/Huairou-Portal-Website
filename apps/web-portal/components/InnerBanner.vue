<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
}>();
</script>

<template>
  <div class="inner-banner">
    <div class="container inner-banner__inner">
      <div class="inner-banner__title">{{ title }}</div>
      <div v-if="subtitle" class="inner-banner__subtitle">{{ subtitle }}</div>
    </div>
  </div>
</template>

<style scoped>
.inner-banner {
  background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
  padding: 36px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.inner-banner__inner {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inner-banner__title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  line-height: 1.3;
}

.inner-banner__subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.62);
  line-height: 1.6;
}
</style>
