<script setup lang="ts">
const { data } = await useSiteSettings();
const profile = computed(() => data.value?.site_profile || {});
const quickLinks = computed(() => data.value?.quick_links || []);
</script>

<template>
  <footer style="padding: 28px 0 40px; border-top: 1px solid rgba(217, 227, 240, 0.7);">
    <div class="container card" style="padding: 28px;">
      <div class="card-grid">
        <div style="grid-column: span 5;">
          <div class="badge">Research Portal</div>
          <div style="font-size: 28px; font-weight: 700; margin-top: 16px;">{{ profile.site_name || "北京怀柔科学城生命科学产业创新研究院" }}</div>
          <div style="margin-top: 14px; color: var(--muted); line-height: 1.7;">
            {{ profile.site_subtitle || "聚焦生命科学成果转化与协同创新服务。" }}
          </div>
        </div>
        <div style="grid-column: span 3;">
          <div style="font-size: 14px; color: var(--muted);">快捷入口</div>
          <div style="margin-top: 14px; display: flex; flex-direction: column; gap: 10px;">
            <NuxtLink v-for="link in quickLinks" :key="link.url" :to="link.url">{{ link.label }}</NuxtLink>
          </div>
        </div>
        <div style="grid-column: span 4;">
          <div style="font-size: 14px; color: var(--muted);">联系方式</div>
          <div style="margin-top: 14px; display: grid; gap: 10px; line-height: 1.7;">
            <div>{{ profile.address }}</div>
            <div>{{ profile.contact_phone }}</div>
            <div>{{ profile.contact_email }}</div>
            <div style="color: var(--muted);">{{ profile.icp_no }}</div>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>
