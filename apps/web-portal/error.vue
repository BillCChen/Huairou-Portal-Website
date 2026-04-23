<script setup lang="ts">
import NotFoundPage from "./pages/404.vue";

const error = useError();
</script>

<template>
  <NotFoundPage v-if="error?.statusCode === 404" />
  <div v-else class="container list-page">
    <div class="card" style="padding: 40px; text-align: center;">
      <div class="badge">{{ error?.statusCode || 500 }}</div>
      <h1 class="section-title" style="margin-top: 18px;">页面暂时不可用</h1>
      <p class="section-desc" style="margin-inline: auto;">
        {{ error?.message || "系统发生未预期错误，请稍后重试。" }}
      </p>
      <NuxtLink class="button" to="/" style="margin-top: 20px;">返回首页</NuxtLink>
    </div>
  </div>
</template>
