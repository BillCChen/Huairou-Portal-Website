<script setup lang="ts">
const { data } = await useSiteSettings();
const profile = computed(() => data.value?.site_profile || {});
const quickLinks = computed(() => data.value?.quick_links || []);
</script>

<template>
  <footer class="site-footer">
    <div class="container site-footer__body">
      <div class="site-footer__col site-footer__col--brand">
        <div class="site-footer__logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="14" stroke="rgba(255,255,255,0.3)" stroke-width="1.5"/>
            <circle cx="16" cy="16" r="7" fill="rgba(255,255,255,0.85)"/>
          </svg>
        </div>
        <div class="site-footer__org">
          {{ profile.site_name || "北京怀柔科学城生命科学产业创新研究院" }}
        </div>
        <div class="site-footer__desc">
          {{ profile.site_subtitle || "聚焦生命科学成果转化与协同创新服务。" }}
        </div>
      </div>

      <div class="site-footer__col">
        <div class="site-footer__col-title">快捷入口</div>
        <div class="site-footer__links">
          <NuxtLink v-for="link in quickLinks" :key="link.url" :to="link.url" class="site-footer__link">
            {{ link.label }}
          </NuxtLink>
          <NuxtLink to="/news" class="site-footer__link">新闻动态</NuxtLink>
          <NuxtLink to="/about" class="site-footer__link">关于我们</NuxtLink>
          <NuxtLink to="/cases" class="site-footer__link">成功案例</NuxtLink>
        </div>
      </div>

      <div class="site-footer__col">
        <div class="site-footer__col-title">联系方式</div>
        <div class="site-footer__contacts">
          <div v-if="profile.address" class="site-footer__contact-item">
            <span class="site-footer__contact-label">地址</span>
            <span>{{ profile.address }}</span>
          </div>
          <div v-if="profile.contact_phone" class="site-footer__contact-item">
            <span class="site-footer__contact-label">电话</span>
            <span>{{ profile.contact_phone }}</span>
          </div>
          <div v-if="profile.contact_email" class="site-footer__contact-item">
            <span class="site-footer__contact-label">邮箱</span>
            <span>{{ profile.contact_email }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="site-footer__bottom">
      <div class="container site-footer__bottom-inner">
        <span>Copyright &copy; {{ new Date().getFullYear() }} 北京怀柔科学城生命科学产业创新研究院</span>
        <span v-if="profile.icp_no">{{ profile.icp_no }}</span>
      </div>
    </div>
  </footer>
</template>

<style scoped>
.site-footer {
  background: var(--primary-dark);
  color: rgba(255, 255, 255, 0.75);
  margin-top: 0;
}

.site-footer__body {
  display: grid;
  grid-template-columns: 2fr 1fr 1.5fr;
  gap: 48px;
  padding: 52px 0 40px;
}

.site-footer__col {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.site-footer__logo {
  margin-bottom: 16px;
}

.site-footer__org {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  line-height: 1.4;
  margin-bottom: 12px;
}

.site-footer__desc {
  font-size: 13px;
  line-height: 1.8;
  color: rgba(255, 255, 255, 0.55);
}

.site-footer__col-title {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 18px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.12);
}

.site-footer__links {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.site-footer__link {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.62);
  text-decoration: none;
  transition: color 0.15s;
}

.site-footer__link:hover {
  color: #fff;
}

.site-footer__contacts {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.site-footer__contact-item {
  display: flex;
  gap: 10px;
  font-size: 13px;
  line-height: 1.6;
}

.site-footer__contact-label {
  color: rgba(255, 255, 255, 0.45);
  flex-shrink: 0;
  width: 28px;
}

.site-footer__bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.site-footer__bottom-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.38);
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .site-footer__body {
    grid-template-columns: 1fr;
    gap: 32px;
  }
}
</style>
