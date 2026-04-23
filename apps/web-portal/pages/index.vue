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
    return `linear-gradient(135deg, rgba(10,46,134,0.82) 0%, rgba(10,78,168,0.55) 100%), url(${imageUrl}) center / cover no-repeat`;
  }
  return "linear-gradient(135deg, #0a2e86 0%, #0a4ea8 60%, #114fb6 100%)";
});

const featuredNews = computed(() => news.value[0] || null);
const sideNews = computed(() => news.value.slice(1, 6));

let bannerTimer: ReturnType<typeof setInterval> | null = null;

const goToBanner = (index: number) => {
  if (!banners.value.length) return;
  currentBannerIndex.value = (index + banners.value.length) % banners.value.length;
};

const nextBanner = () => goToBanner(currentBannerIndex.value + 1);

onMounted(() => {
  bannerTimer = setInterval(() => {
    if (banners.value.length > 1) nextBanner();
  }, 5000);
});

onBeforeUnmount(() => {
  if (bannerTimer) clearInterval(bannerTimer);
});

useSeoMeta({
  title: () => profile.value.site_name || "北京怀柔科学城生命科学产业创新研究院",
  description: () => profile.value.site_subtitle || "聚焦生命科学成果转化与创新协同，服务研究、产业与人才资源对接。",
});
</script>

<template>
  <div>
    <!-- ── Hero Banner ───────────────────────────────── -->
    <section class="hero" :style="{ background: heroBackground }">
      <div class="container hero__inner">
        <div class="hero__content">
          <div class="hero__tag">LIFE SCIENCE · INNOVATION · RESEARCH</div>
          <h1 class="hero__title">
            {{ activeBanner?.title || profile.site_name || "聚焦生命科学成果转化，打造开放协同的创新门户" }}
          </h1>
          <p class="hero__subtitle">
            {{ activeBanner?.subtitle || profile.site_subtitle || "服务研究、产业与人才资源对接，推动科技成果走向产业化" }}
          </p>
          <div class="hero__actions">
            <NuxtLink
              v-if="activeBanner?.button_text && activeBanner?.button_url"
              class="button"
              :to="activeBanner.button_url"
              style="padding: 11px 28px; font-size: 15px;"
            >
              {{ activeBanner.button_text }}
            </NuxtLink>
            <NuxtLink v-else class="button" to="/news" style="padding: 11px 28px; font-size: 15px;">
              查看新闻动态
            </NuxtLink>
            <NuxtLink class="button outline-white" to="/about" style="padding: 11px 28px; font-size: 15px;">
              了解研究院
            </NuxtLink>
          </div>
        </div>

        <div v-if="quickLinks.length" class="hero__quick">
          <NuxtLink
            v-for="link in quickLinks.slice(0, 4)"
            :key="link.url"
            :to="link.url"
            class="hero__quick-item"
          >
            <span class="hero__quick-icon">→</span>
            <span>{{ link.label }}</span>
          </NuxtLink>
        </div>
      </div>

      <!-- Banner dots -->
      <div v-if="banners.length > 1" class="hero__dots">
        <button
          v-for="(banner, index) in banners"
          :key="banner.id || index"
          type="button"
          class="hero__dot"
          :class="{ 'is-active': index === currentBannerIndex }"
          :aria-label="`切换到第 ${index + 1} 张`"
          @click="goToBanner(index)"
        />
      </div>
    </section>

    <!-- ── Quick Stats Bar ────────────────────────────── -->
    <div v-if="homeStats.length" class="stats-bar">
      <div class="container stats-bar__inner">
        <div v-for="item in homeStats" :key="item.label" class="stats-bar__item">
          <span class="stats-bar__value">{{ item.value }}</span>
          <span class="stats-bar__label">{{ item.label }}</span>
        </div>
      </div>
    </div>

    <!-- ── News Center ────────────────────────────────── -->
    <section class="section" style="background: var(--bg-white);">
      <div class="container">
        <div class="section-header">
          <div>
            <div class="section-header__title">新闻动态</div>
            <div class="section-header__sub">围绕研究院新闻、通知公告与行业资讯，形成统一的内容发布入口</div>
          </div>
          <NuxtLink to="/news" class="section-header__more">更多新闻 →</NuxtLink>
        </div>

        <div class="news-layout">
          <!-- Featured news (left) -->
          <div class="news-featured">
            <NuxtLink v-if="featuredNews" :to="`/news/${featuredNews.slug}`" class="news-featured__card">
              <div class="news-featured__img-wrap">
                <div
                  class="news-featured__img"
                  :style="featuredNews.image_url
                    ? `background-image: url(${featuredNews.image_url})`
                    : ''"
                />
              </div>
              <div class="news-featured__meta">
                <span class="news-featured__source">{{ featuredNews.source || "研究院资讯" }}</span>
                <span class="news-featured__date">{{ featuredNews.publish_at?.slice?.(0, 10) || "" }}</span>
              </div>
              <div class="news-featured__title">{{ featuredNews.title }}</div>
              <div class="news-featured__summary">{{ featuredNews.summary }}</div>
            </NuxtLink>
            <div v-else class="news-featured__card news-featured__placeholder">
              暂无新闻
            </div>
          </div>

          <!-- News list (right) -->
          <div class="news-list">
            <NuxtLink
              v-for="item in sideNews"
              :key="item.slug"
              :to="`/news/${item.slug}`"
              class="news-list__item"
            >
              <div class="news-list__title">{{ item.title }}</div>
              <div class="news-list__meta">
                <span>{{ item.source }}</span>
                <span>{{ item.publish_at?.slice?.(0, 10) || "" }}</span>
              </div>
            </NuxtLink>
            <NuxtLink v-if="!sideNews.length && !featuredNews" to="/news" class="news-list__item">
              前往新闻中心
            </NuxtLink>
          </div>
        </div>
      </div>
    </section>

    <!-- ── About Us ───────────────────────────────────── -->
    <section class="section" style="background: var(--bg-light);">
      <div class="container">
        <div class="about-layout">
          <div class="about-content">
            <div class="section-header" style="margin-bottom: 20px;">
              <div>
                <div class="section-header__title">关于我们</div>
                <div class="section-header__sub">{{ about.title }}</div>
              </div>
            </div>
            <div class="rich-content" v-html="about.content_html" style="max-height: 240px; overflow: hidden;" />
            <NuxtLink to="/about" class="button" style="margin-top: 24px; display: inline-flex;">
              了解详情
            </NuxtLink>
          </div>
          <div class="about-visual">
            <div class="about-visual__inner">
              <div v-if="homeStats.length" class="about-stats">
                <div v-for="item in homeStats" :key="item.label" class="about-stats__item">
                  <div class="about-stats__value">{{ item.value }}</div>
                  <div class="about-stats__label">{{ item.label }}</div>
                </div>
              </div>
              <div v-else class="about-visual__placeholder" />
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Cases ─────────────────────────────────────── -->
    <section class="section" style="background: var(--bg-white);">
      <div class="container">
        <div class="section-header">
          <div>
            <div class="section-header__title">成功案例</div>
            <div class="section-header__sub">展示典型科技成果转化案例</div>
          </div>
          <NuxtLink to="/cases" class="section-header__more">更多案例 →</NuxtLink>
        </div>
        <div class="cases-grid">
          <NuxtLink
            v-for="item in cases.slice(0, 4)"
            :key="item.slug"
            :to="`/cases/${item.slug}`"
            class="case-card"
          >
            <div class="case-card__stage">{{ item.stage || "成果转化" }}</div>
            <div class="case-card__title">{{ item.title }}</div>
            <div class="case-card__summary">{{ item.summary }}</div>
            <div v-if="(item.highlights || []).length" class="case-card__tags">
              <span v-for="h in (item.highlights || []).slice(0, 2)" :key="h" class="case-card__tag">
                {{ h }}
              </span>
            </div>
            <span class="case-card__more">查看详情 →</span>
          </NuxtLink>
          <!-- placeholder cards when data is empty -->
          <template v-if="!cases.length">
            <div v-for="n in 4" :key="n" class="case-card case-card--empty">
              <div class="case-card__stage">案例</div>
              <div class="case-card__title">案例标题占位</div>
            </div>
          </template>
        </div>
      </div>
    </section>

    <!-- ── Partners ───────────────────────────────────── -->
    <section class="partners-section">
      <div class="container">
        <div class="section-header" style="border-left-color: rgba(255,255,255,0.4); margin-bottom: 28px;">
          <div>
            <div class="section-header__title" style="color: #fff;">合作伙伴</div>
            <div class="section-header__sub" style="color: rgba(255,255,255,0.6);">联合高校、科研院所与领军企业，共同推动技术转化与产业协同</div>
          </div>
        </div>
        <div class="partners-grid">
          <div
            v-for="link in quickLinks"
            :key="link.url"
            class="partner-card"
          >
            <NuxtLink :to="link.url" class="partner-card__inner">
              {{ link.label }}
            </NuxtLink>
          </div>
          <!-- placeholder when no data -->
          <template v-if="!quickLinks.length">
            <div v-for="n in 6" :key="n" class="partner-card">
              <div class="partner-card__inner partner-card__inner--empty" />
            </div>
          </template>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── Hero ──────────────────────────────────────────── */
.hero {
  position: relative;
  min-height: 480px;
  display: flex;
  align-items: center;
}

.hero__inner {
  padding: 72px 0 80px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.hero__content {
  max-width: 700px;
}

.hero__tag {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
  letter-spacing: 0.12em;
  margin-bottom: 18px;
}

.hero__title {
  font-size: clamp(28px, 4.5vw, 46px);
  font-weight: 700;
  color: #fff;
  line-height: 1.25;
  margin: 0 0 18px;
}

.hero__subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.72);
  line-height: 1.8;
  margin: 0 0 32px;
  max-width: 560px;
}

.hero__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero__quick {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 40px;
  padding-top: 28px;
  border-top: 1px solid rgba(255, 255, 255, 0.15);
}

.hero__quick-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 2px;
  color: #fff;
  font-size: 13px;
  text-decoration: none;
  transition: background 0.15s;
}

.hero__quick-item:hover {
  background: rgba(255, 255, 255, 0.18);
}

.hero__quick-icon {
  font-size: 12px;
  opacity: 0.7;
}

.hero__dots {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
}

.hero__dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  border: none;
  background: rgba(255, 255, 255, 0.35);
  cursor: pointer;
  padding: 0;
  transition: background 0.15s, width 0.2s;
}

.hero__dot.is-active {
  background: #fff;
  width: 20px;
}

/* ── Stats Bar ─────────────────────────────────────── */
.stats-bar {
  background: var(--primary);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.stats-bar__inner {
  display: flex;
  align-items: stretch;
  justify-content: center;
}

.stats-bar__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 18px 40px;
  border-right: 1px solid rgba(255, 255, 255, 0.12);
  flex: 1;
  text-align: center;
}

.stats-bar__item:last-child {
  border-right: none;
}

.stats-bar__value {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.stats-bar__label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.62);
  margin-top: 4px;
}

/* ── News Layout ────────────────────────────────────── */
.news-layout {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 24px;
  align-items: start;
}

.news-featured__card {
  display: block;
  text-decoration: none;
  color: inherit;
}

.news-featured__img-wrap {
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 14px;
  aspect-ratio: 16 / 9;
  background: var(--bg-light);
}

.news-featured__img {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #0a4ea8, #114fb6);
  background-size: cover;
  background-position: center;
  transition: transform 0.3s;
}

.news-featured__card:hover .news-featured__img {
  transform: scale(1.02);
}

.news-featured__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--muted);
  font-size: 14px;
  border: 1px dashed var(--border);
  border-radius: 4px;
}

.news-featured__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}

.news-featured__source {
  font-size: 12px;
  color: var(--primary);
  background: rgba(10, 78, 168, 0.08);
  padding: 3px 8px;
  border-radius: 2px;
}

.news-featured__date {
  font-size: 12px;
  color: var(--muted);
}

.news-featured__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.45;
  margin-bottom: 10px;
  transition: color 0.15s;
}

.news-featured__card:hover .news-featured__title {
  color: var(--primary);
}

.news-featured__summary {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.8;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-list {
  display: flex;
  flex-direction: column;
  border-top: 2px solid var(--primary);
}

.news-list__item {
  display: block;
  padding: 16px 0;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
}

.news-list__item:hover .news-list__title {
  color: var(--primary);
}

.news-list__title {
  font-size: 14px;
  color: var(--text);
  line-height: 1.5;
  margin-bottom: 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  transition: color 0.15s;
}

.news-list__meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
}

/* ── About Layout ───────────────────────────────────── */
.about-layout {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 48px;
  align-items: center;
}

.about-visual__inner {
  background: var(--primary);
  border-radius: 4px;
  padding: 32px;
  min-height: 280px;
}

.about-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.about-stats__item {
  padding: 20px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 4px;
  text-align: center;
}

.about-stats__value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.about-stats__label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin-top: 6px;
}

.about-visual__placeholder {
  height: 100%;
  min-height: 220px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
}

/* ── Cases Grid ─────────────────────────────────────── */
.cases-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.case-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 24px;
  background: var(--bg-white);
  border: 1px solid var(--border);
  border-radius: 4px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.case-card:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 16px rgba(10, 78, 168, 0.1);
}

.case-card__stage {
  font-size: 12px;
  color: var(--primary);
  background: rgba(10, 78, 168, 0.08);
  padding: 3px 8px;
  border-radius: 2px;
  width: fit-content;
}

.case-card__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
}

.case-card:hover .case-card__title {
  color: var(--primary);
}

.case-card__summary {
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.case-card__tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.case-card__tag {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg-light);
  border: 1px solid var(--border);
  border-radius: 2px;
  color: var(--muted);
}

.case-card__more {
  font-size: 13px;
  color: var(--primary);
  margin-top: 4px;
}

.case-card--empty {
  opacity: 0.4;
  pointer-events: none;
}

/* ── Partners Section ───────────────────────────────── */
.partners-section {
  background: var(--primary-dark);
  padding: 56px 0;
}

.partners-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.partner-card {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 4px;
  transition: background 0.15s;
}

.partner-card:hover {
  background: rgba(255, 255, 255, 0.15);
}

.partner-card__inner {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 72px;
  padding: 16px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  text-align: center;
  font-weight: 600;
}

.partner-card__inner:hover {
  color: #fff;
}

.partner-card__inner--empty {
  min-height: 72px;
}

/* ── Responsive ─────────────────────────────────────── */
@media (max-width: 960px) {
  .news-layout {
    grid-template-columns: 1fr;
  }

  .about-layout {
    grid-template-columns: 1fr;
  }

  .cases-grid {
    grid-template-columns: 1fr;
  }

  .partners-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stats-bar__inner {
    flex-wrap: wrap;
  }

  .stats-bar__item {
    flex: 1 1 50%;
    border-right: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
  }
}
</style>
