<script setup lang="ts">
const { data } = await useAsyncData("home", () => usePortalApi<any>("/public/home"));
const banners = computed(() => data.value?.banners || []);
const news = computed(() => data.value?.news || []);
const cases = computed(() => data.value?.cases || []);
const about = computed(() => data.value?.about || {});
const siteSettings = computed(() => data.value?.site_settings || {});
const profile = computed(() => siteSettings.value.site_profile || {});
const homeStats = computed(() => siteSettings.value.home_stats || []);
const quickLinks = computed(() => siteSettings.value.quick_links || []);
const currentBannerIndex = ref(0);

const activeBanner = computed(() => banners.value[currentBannerIndex.value] || null);
const heroBackground = computed(() => {
  const imageUrl = activeBanner.value?.image_url || activeBanner.value?.image || "";
  if (imageUrl) {
    return `linear-gradient(135deg, rgba(15, 91, 120, 0.78), rgba(42, 125, 111, 0.56)), url(${imageUrl}) center / cover`;
  }
  return "linear-gradient(135deg, #0f5b78, #2a7d6f 58%, #d29b3d)";
});

let bannerTimer: ReturnType<typeof setInterval> | null = null;

const goToBanner = (index: number) => {
  if (!banners.value.length) return;
  currentBannerIndex.value = (index + banners.value.length) % banners.value.length;
};

const nextBanner = () => {
  goToBanner(currentBannerIndex.value + 1);
};

const previousBanner = () => {
  goToBanner(currentBannerIndex.value - 1);
};

onMounted(() => {
  bannerTimer = setInterval(() => {
    if (banners.value.length > 1) {
      nextBanner();
    }
  }, 5000);
});

onBeforeUnmount(() => {
  if (bannerTimer) {
    clearInterval(bannerTimer);
  }
});

useSeoMeta({
  title: () => profile.value.site_name || "北京怀柔科学城生命科学产业创新研究院",
  description: () => profile.value.site_subtitle || "聚焦生命科学成果转化与创新协同，服务研究、产业与人才资源对接。",
});
</script>

<template>
  <div>
    <section class="section" style="padding-top: 44px;">
      <div class="container card" style="padding: 28px;">
        <div class="card-grid" style="align-items: stretch;">
          <div style="grid-column: span 7; padding: 18px;">
            <div class="badge">Official Portal</div>
            <h1 style="font-size: clamp(38px, 6vw, 64px); line-height: 1.06; margin: 18px 0 0;">
              {{ activeBanner?.title || "聚焦生命科学成果转化，打造开放协同的创新门户" }}
            </h1>
            <p class="section-desc" style="font-size: 18px; margin-top: 20px;">
              {{ activeBanner?.subtitle || profile.site_subtitle }}
            </p>
            <div style="display: flex; gap: 12px; margin-top: 28px; flex-wrap: wrap;">
              <NuxtLink
                v-if="activeBanner?.button_text && activeBanner?.button_url"
                class="button"
                :to="activeBanner.button_url"
              >
                {{ activeBanner.button_text }}
              </NuxtLink>
              <NuxtLink v-else class="button" to="/news">查看新闻动态</NuxtLink>
              <NuxtLink class="button secondary" to="/about">了解研究院</NuxtLink>
            </div>
            <div v-if="banners.length > 1" style="display: flex; gap: 10px; margin-top: 24px; align-items: center; flex-wrap: wrap;">
              <button class="button secondary" @click="previousBanner">上一张</button>
              <button class="button secondary" @click="nextBanner">下一张</button>
              <div style="display: flex; gap: 8px;">
                <button
                  v-for="(banner, index) in banners"
                  :key="banner.id || index"
                  type="button"
                  :aria-label="`切换到第 ${index + 1} 张 Banner`"
                  @click="goToBanner(index)"
                  style="width: 12px; height: 12px; border-radius: 999px; border: none; cursor: pointer; background: #cbd5e1;"
                  :style="index === currentBannerIndex ? 'background:#0f5b78;' : ''"
                />
              </div>
            </div>
          </div>
          <div style="grid-column: span 5; position: relative; min-height: 320px;">
            <div
              style="position: absolute; inset: 0; border-radius: 28px; transition: background 0.4s ease;"
              :style="{ background: heroBackground }"
            />
            <div style="position: absolute; inset: 16px; border-radius: 22px; background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.25);"></div>
            <div style="position: absolute; left: 28px; bottom: 28px; color: white;">
              <div style="font-size: 14px; opacity: 0.84;">Research · Industry · Service</div>
              <div style="font-size: 28px; font-weight: 700; margin-top: 10px;">{{ activeBanner?.title || "CMS-Driven Portal" }}</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <div class="section-title">机构概况</div>
        <div class="section-desc">{{ about.title }}。{{ profile.site_subtitle }}</div>
        <div class="card-grid" style="margin-top: 26px;">
          <article class="card" style="grid-column: span 6; padding: 28px;">
            <div class="rich-content" v-html="about.content_html" />
            <NuxtLink to="/about" class="button secondary" style="margin-top: 24px;">查看详情</NuxtLink>
          </article>
          <div class="card" style="grid-column: span 6; padding: 20px;">
            <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px;">
              <div v-for="item in homeStats" :key="item.label" style="padding: 18px; border-radius: 18px; background: #f8fbff; border: 1px solid var(--line);">
                <div style="font-size: 13px; color: var(--muted);">{{ item.label }}</div>
                <div style="font-size: 34px; font-weight: 700; margin-top: 8px;">{{ item.value }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <div style="display: flex; justify-content: space-between; gap: 16px; align-items: end; flex-wrap: wrap;">
          <div>
            <div class="section-title">新闻动态</div>
            <div class="section-desc">围绕研究院新闻、通知公告与行业资讯，形成统一的内容发布入口。</div>
          </div>
          <NuxtLink to="/news" class="button secondary">进入新闻中心</NuxtLink>
        </div>
        <div class="card-grid" style="margin-top: 26px;">
          <article v-for="item in news" :key="item.slug" class="card" style="grid-column: span 4; padding: 22px;">
            <div class="badge">News</div>
            <h3 style="font-size: 24px; margin: 18px 0 0;">{{ item.title }}</h3>
            <p style="color: var(--muted); line-height: 1.8; min-height: 96px;">{{ item.summary }}</p>
            <div style="display: flex; justify-content: space-between; color: var(--muted); font-size: 14px;">
              <span>{{ item.source }}</span>
              <span>{{ item.publish_at?.slice?.(0, 10) || "" }}</span>
            </div>
            <NuxtLink :to="`/news/${item.slug}`" class="button secondary" style="margin-top: 18px;">查看详情</NuxtLink>
          </article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container">
        <div style="display: flex; justify-content: space-between; gap: 16px; align-items: end; flex-wrap: wrap;">
          <div>
            <div class="section-title">成功案例</div>
            <div class="section-desc">展示典型科技成果转化案例，敏感字段仍保持可配置和可关闭状态。</div>
          </div>
          <NuxtLink to="/cases" class="button secondary">浏览案例</NuxtLink>
        </div>
        <div class="card-grid" style="margin-top: 26px;">
          <article v-for="item in cases" :key="item.slug" class="card" style="grid-column: span 4; padding: 22px;">
            <div class="badge">{{ item.stage || "Case" }}</div>
            <h3 style="font-size: 24px; margin: 18px 0 0;">{{ item.title }}</h3>
            <p style="color: var(--muted); line-height: 1.8; min-height: 96px;">{{ item.summary }}</p>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <span v-for="highlight in item.highlights || []" :key="highlight" class="badge" style="background: #f4efe4; color: #7b5a17;">
                {{ highlight }}
              </span>
            </div>
            <NuxtLink :to="`/cases/${item.slug}`" class="button secondary" style="margin-top: 18px;">进入详情</NuxtLink>
          </article>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container card" style="padding: 28px;">
        <div class="section-title">快速入口</div>
        <div class="section-desc">研究所展示、人才服务和在线服务均已预留路径与页面，可根据甲方确认结果决定公开深度。</div>
        <div class="card-grid" style="margin-top: 24px;">
          <NuxtLink v-for="link in quickLinks" :key="link.url" :to="link.url" class="card" style="grid-column: span 3; padding: 22px; background: #f8fbff;">
            <div style="font-size: 13px; color: var(--muted);">Quick Link</div>
            <div style="font-size: 22px; font-weight: 700; margin-top: 12px;">{{ link.label }}</div>
          </NuxtLink>
        </div>
      </div>
    </section>
  </div>
</template>
