<script setup lang="ts">
const route = useRoute();
const router = useRouter();

const NEWS_CATEGORY_SCOPES = [
  { key: "internal", label: "院内新闻", fallbackSlug: "院内新闻", aliases: ["院内新闻", "institution-news", "institution", "internal-news"] },
  { key: "industry", label: "行业资讯", fallbackSlug: "行业资讯", aliases: ["行业资讯", "industry-news", "industry", "trade-news"] },
  { key: "notice", label: "通知公告", fallbackSlug: "通知公告", aliases: ["通知公告", "notice", "announcement", "notice-announcement"] },
  { key: "media", label: "媒体聚焦", fallbackSlug: "媒体聚焦", aliases: ["媒体聚焦", "media-focus", "media", "media-news"] },
] as const;

const page = computed(() => Math.max(1, Number(route.query.page || 1)));
const keyword = computed(() => String(route.query.keyword || ""));
const currentCategory = computed(() => String(route.query.category_slug || ""));

const normalizeCategoryText = (value: any) => {
  return String(value || "").trim().toLowerCase();
};

const resolveCategoryKey = (raw: any) => {
  const target = normalizeCategoryText(raw);
  if (!target) {
    return "";
  }

  const matched = NEWS_CATEGORY_SCOPES.find((scope) =>
    [scope.label, scope.fallbackSlug, scope.key, ...scope.aliases].some((alias) => normalizeCategoryText(alias) === target)
  );

  return matched?.key || "";
};

const categoryTabs = computed(() => {
  const mapped = new Map<string, string>();
  (categories.value || []).forEach((item: any) => {
    const key = resolveCategoryKey(item?.slug || item?.name || item?.title || item?.label || item?.category);
    if (!key) {
      return;
    }
    if (mapped.has(key)) {
      return;
    }
    mapped.set(key, String(item?.slug || item?.name || item?.title || ""));
  });

  return [
    { label: "全部", slug: "", key: "all" },
    ...NEWS_CATEGORY_SCOPES.map((scope) => ({
      label: scope.label,
      slug: mapped.get(scope.key) || scope.fallbackSlug,
      key: scope.key,
    })),
  ];
});

const activeCategoryKey = computed(() => {
  if (!currentCategory.value) {
    return "all";
  }
  return resolveCategoryKey(currentCategory.value) || "custom";
});

const categoryParam = computed(() => {
  if (!currentCategory.value) {
    return "";
  }
  if (activeCategoryKey.value === "custom") {
    return currentCategory.value;
  }
  const tab = categoryTabs.value.find((item) => item.key === activeCategoryKey.value);
  return tab?.slug || currentCategory.value;
});

const { data: home } = await useAsyncData("home", () => usePortalApi<any>("/public/home"));
const { data: categories } = await useAsyncData("home-news-categories", () =>
  usePortalApi<any[]>("/public/categories", {
    query: { type: "news" },
  })
);
const { data: newsData, pending, error } = await useAsyncData(
  () => `home-news-${page.value}-${categoryParam.value}-${keyword.value}`,
  () =>
    usePortalApi<any>("/public/news", {
      query: {
        page: page.value,
        page_size: 6,
        category: categoryParam.value || undefined,
        keyword: keyword.value || undefined,
      },
    }),
  { watch: [page, categoryParam, keyword] }
);


const siteProfile = computed(() => home.value?.site_settings?.site_profile || {});
const banners = computed(() => home.value?.banners || []);
const heroItem = computed(() => banners.value[0] || {});
const heroImage = computed(() => {
  const item = heroItem.value;
  return item?.image || item?.image_url || item?.cover || item?.cover_url || "";
});
const heroTitle = computed(() => heroItem.value?.title || "依托人工智能技术 赋能科研创新与产业服务");
const heroSubTitle = computed(
  () => heroItem.value?.subtitle || heroItem.value?.description || "提升科创要素整合效率，强化科技成果转化的精准对接能力"
);
const heroTabs = computed(() => "请输入需求、技术、企业或服务关键词");

const newsItems = computed(() => newsData.value?.items || []);
const carouselItems = computed(() => newsItems.value.slice(0, 5));
const activeCarouselIndex = ref(0);
const featured = computed(() => carouselItems.value[activeCarouselIndex.value] || newsItems.value[0] || null);
const newsList = computed(() => {
  return carouselItems.value;
});
let carouselTimer: ReturnType<typeof setInterval> | null = null;

const stopCarousel = () => {
  if (!carouselTimer) {
    return;
  }
  clearInterval(carouselTimer);
  carouselTimer = null;
};

const showCarouselItem = (index: number) => {
  const length = carouselItems.value.length;
  if (!length) {
    activeCarouselIndex.value = 0;
    return;
  }
  activeCarouselIndex.value = (index + length) % length;
};

const nextCarouselItem = () => {
  showCarouselItem(activeCarouselIndex.value + 1);
};

const prevCarouselItem = () => {
  showCarouselItem(activeCarouselIndex.value - 1);
};

const startCarousel = () => {
  stopCarousel();
  if (carouselItems.value.length <= 1) {
    return;
  }
  carouselTimer = setInterval(nextCarouselItem, 3000);
};

const restartCarousel = () => {
  startCarousel();
};

watch(
  () => carouselItems.value.map((item: any) => item.slug || item.id).join("|"),
  () => {
    activeCarouselIndex.value = 0;
    if (import.meta.client) {
      startCarousel();
    }
  }
);

onMounted(startCarousel);
onBeforeUnmount(stopCarousel);

const searchKeyword = ref(keyword.value);

watch(
  keyword,
  (value) => {
    searchKeyword.value = value;
  },
  { immediate: true }
);

const totalPages = computed(() => Number(newsData.value?.total_pages || 0));

const buildQuery = async (next: Record<string, string | number | undefined>) => {
  const query = { ...route.query, ...next } as Record<string, string | number | undefined>;

  Object.keys(query).forEach((key) => {
    const val = query[key];
    if (val == null || val === "") {
      delete query[key];
    }
  });

  await router.push({ query });
};

const submitSearch = async () => {
  await buildQuery({ page: 1, keyword: searchKeyword.value || undefined, category_slug: categoryParam.value || undefined });
};

const selectCategory = async (slug: string) => {
  await buildQuery({ page: 1, category_slug: slug || undefined, keyword: keyword.value || undefined });
};

const isCategoryActive = (tab: { slug: string; key: string }) => {
  if (activeCategoryKey.value === "all") {
    return tab.key === "all";
  }
  if (activeCategoryKey.value === "custom") {
    return normalizeCategoryText(tab.slug) === normalizeCategoryText(currentCategory.value);
  }
  return tab.key === activeCategoryKey.value;
};

const resolveNewsCategoryLabel = (item: any) => {
  const key = resolveCategoryKey(
    item?.category
      || item?.category_slug
      || item?.category_name
      || item?.tag
      || item?.source
      || item?.type
      || item?.labels?.[0]
  );
  if (key === "internal") {
    return "院内新闻";
  }
  if (key === "industry") {
    return "行业资讯";
  }
  if (key === "notice") {
    return "通知公告";
  }
  if (key === "media") {
    return "媒体聚焦";
  }
  return item?.source || item?.category_name || item?.category || "新闻";
};

const changePage = async (nextPage: number) => {
  if (nextPage < 1 || (totalPages.value && nextPage > totalPages.value)) {
    return;
  }
  await buildQuery({ page: nextPage });
};

const formatNewsDate = (value?: string) => {
  if (!value) {
    return "";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value.slice(0, 10);
  }
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y} 年 ${m} 月 ${d} 日`;
};

const resolveImage = (item: any) => item?.cover || item?.image || item?.image_url || item?.thumbnail || item?.cover_url || "";

const resolveThumbClass = (index: number) => {
  const styles = ["thumb--room", "thumb--building", "thumb--stage", "thumb--screen"];
  return styles[index % styles.length];
};

useSeoMeta({
  title: () => `${siteProfile.value?.site_name || "北京怀柔科学城生命科学产业创新研究院"} - 首页`,
  description: () => heroSubTitle.value,
});
</script>

<template>
  <div class="home-page">
    <section class="hero-shell">
      <div class="hero-bg-grid" aria-hidden="true" />
      <svg class="hero-dna hero-dna--left" viewBox="0 0 160 100" aria-hidden="true">
        <path d="M36 0 C112 20 34 80 116 100" fill="none" stroke="rgba(118,238,255,0.85)" stroke-width="2" />
        <path d="M118 0 C36 20 112 80 44 100" fill="none" stroke="rgba(118,238,255,0.55)" stroke-width="2" />
        <g stroke="rgba(190,250,255,0.66)" stroke-width="1.4">
          <path d="M50 11 L106 11" />
          <path d="M60 27 L96 27" />
          <path d="M66 44 L89 44" />
          <path d="M64 61 L92 61" />
          <path d="M54 78 L103 78" />
        </g>
        <g fill="rgba(205,252,255,0.88)">
          <circle cx="38" cy="5" r="2" />
          <circle cx="54" cy="21" r="2" />
          <circle cx="66" cy="44" r="2" />
          <circle cx="56" cy="77" r="2" />
          <circle cx="117" cy="7" r="2" />
          <circle cx="98" cy="29" r="2" />
          <circle cx="90" cy="61" r="2" />
        </g>
      </svg>
      <svg class="hero-dna hero-dna--right" viewBox="0 0 160 100" aria-hidden="true">
        <path d="M36 0 C112 20 34 80 116 100" fill="none" stroke="rgba(118,238,255,0.85)" stroke-width="2" />
        <path d="M118 0 C36 20 112 80 44 100" fill="none" stroke="rgba(118,238,255,0.55)" stroke-width="2" />
        <g stroke="rgba(190,250,255,0.66)" stroke-width="1.4">
          <path d="M50 11 L106 11" />
          <path d="M60 27 L96 27" />
          <path d="M66 44 L89 44" />
          <path d="M64 61 L92 61" />
          <path d="M54 78 L103 78" />
        </g>
        <g fill="rgba(205,252,255,0.88)">
          <circle cx="38" cy="5" r="2" />
          <circle cx="54" cy="21" r="2" />
          <circle cx="66" cy="44" r="2" />
          <circle cx="56" cy="77" r="2" />
          <circle cx="117" cy="7" r="2" />
          <circle cx="98" cy="29" r="2" />
          <circle cx="90" cy="61" r="2" />
        </g>
      </svg>

      <div class="hero-copy-wrap">
        <h1 class="hero-title">{{ heroTitle }}</h1>
        <p class="hero-subtitle">{{ heroSubTitle }}</p>
        <form class="hero-search" @submit.prevent="submitSearch">
          <label class="hero-search__input-wrap" for="home-keyword">
            <span class="hero-search__placeholder">{{ heroTabs }}</span>
            <input
              id="home-keyword"
              v-model="searchKeyword"
              type="text"
              class="hero-search__input"
              autocomplete="off"
            />
          </label>
          <button type="submit" class="hero-search__btn">智能搜索</button>
        </form>
      </div>

      <div class="hero-media">
        <img v-if="heroImage" :src="heroImage" alt="hero" loading="lazy" />
        <div v-else class="hero-media__fallback">DATA</div>
      </div>
    </section>

    <section class="news-section">
      <div class="news-inner container">
        <div class="news-headline">
          <h2 class="news-title">
            <small>NEWS</small>
            <strong>新闻中心</strong>
          </h2>
          <nav class="news-tabs" aria-label="新闻分类">
            <button
              v-for="tab in categoryTabs"
              :key="tab.slug || 'all'"
              class="news-tab"
              :class="{ active: isCategoryActive(tab) }"
              type="button"
              @click="selectCategory(tab.slug)"
            >
              {{ tab.label }}
            </button>
          </nav>
        </div>

        <div class="news-grid">
          <article class="featured-card" @mouseenter="stopCarousel" @mouseleave="restartCarousel">
            <button
              v-if="carouselItems.length > 1"
              class="featured-arrow featured-arrow--prev"
              type="button"
              aria-label="上一条新闻"
              @click="prevCarouselItem"
            >
              ‹
            </button>
            <button
              v-if="carouselItems.length > 1"
              class="featured-arrow featured-arrow--next"
              type="button"
              aria-label="下一条新闻"
              @click="nextCarouselItem"
            >
              ›
            </button>

            <template v-if="featured">
              <Transition name="featured-fade" mode="out-in">
                <div :key="featured.slug || featured.id" class="featured-slide">
                  <div class="featured-cover" v-if="resolveImage(featured)">
                    <img :src="resolveImage(featured)" :alt="featured.title" loading="lazy" />
                    <span class="featured-chip">头条</span>
                  </div>
                  <div v-else class="featured-card__fallback" :class="resolveThumbClass(activeCarouselIndex)" />

                  <div class="featured-caption-wrap">
                    <div class="featured-title">
                      <h3 class="featured-subtitle">{{ resolveNewsCategoryLabel(featured) }}</h3>
                      <h2 class="featured-heading">{{ featured.title }}</h2>
                    </div>
                    <time class="featured-date">{{ formatNewsDate(featured.publish_at || featured.created_at) }}</time>
                    <p class="featured-summary">{{ featured.summary || "暂无摘要" }}</p>
                    <NuxtLink :to="`/news/${featured.slug}`" class="featured-more">查看详情</NuxtLink>
                  </div>
                </div>
              </Transition>

              <div v-if="carouselItems.length > 1" class="featured-dots" aria-label="新闻轮播分页">
                <button
                  v-for="(item, index) in carouselItems"
                  :key="item.slug || item.id"
                  class="featured-dot"
                  :class="{ active: index === activeCarouselIndex }"
                  type="button"
                  :aria-label="`切换到第 ${index + 1} 条新闻`"
                  @click="showCarouselItem(index)"
                />
              </div>
            </template>

            <template v-else>
              <div class="featured-card__fallback" />
              <div class="featured-caption-wrap">
                <h3 class="featured-subtitle">研究院资讯</h3>
                <h2 class="featured-heading">暂无新闻</h2>
                <p class="featured-summary">当前未查询到符合条件的新闻，请尝试切换分类或重新搜索。</p>
              </div>
            </template>
          </article>

          <div class="news-list-wrap">
            <div v-if="pending" class="news-state">正在加载中…</div>
            <div v-else-if="error" class="news-state news-state--error">
              {{ error.data?.message || error.data?.detail || error.message || "新闻加载失败" }}
            </div>
            <template v-else>
              <article
                v-for="(item, index) in newsList"
                :key="item.slug"
                class="news-item"
                :class="{ active: index === activeCarouselIndex }"
                @click="showCarouselItem(index)"
              >
                <div
                  class="news-item-thumb"
                  :class="resolveThumbClass(index)"
                  :style="resolveImage(item) ? { backgroundImage: `url(${resolveImage(item)})` } : undefined"
                ></div>
                <div class="news-item-content">
                  <p class="news-item-tag">{{ resolveNewsCategoryLabel(item) }}</p>
                  <h3>
                    <NuxtLink :to="`/news/${item.slug}`">{{ item.title }}</NuxtLink>
                  </h3>
                  <p>{{ item.summary || "暂无摘要" }}</p>
                </div>
              </article>
              <article v-if="!newsList.length" class="news-empty">暂无更多列表新闻</article>
            </template>
          </div>
        </div>

        <div class="news-more-wrap">
          <NuxtLink class="news-more" to="/news">查看更多</NuxtLink>
        </div>

        <div v-if="totalPages > 1" class="news-pagination">
          <button class="news-pager" :disabled="page <= 1" type="button" @click="changePage(page - 1)">上一页</button>
          <span>第 {{ page }} / {{ totalPages }} 页</span>
          <button class="news-pager" :disabled="page >= totalPages" type="button" @click="changePage(page + 1)">下一页</button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-page {
  --nav-blue: #0c238b;
  --hero-blue: #133eab;
  --hero-deep: #08206d;
  --accent: #1c5dbd;
  --ink: #222d44;
  --muted: #727d91;
  --line: #e7ebf2;
  --paper: #f5f8fc;
  --white: #fbfdff;

  min-height: calc(100vh - 110px);
  background: var(--paper);
  color: var(--ink);
  font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
}

.hero-shell {
  position: relative;
  height: clamp(240px, 32vw, 368px);
  overflow: hidden;
  color: #fff;
  background:
    radial-gradient(circle at 51% 84%, rgba(161, 244, 255, 0.95) 0 1px, transparent 58px),
    radial-gradient(circle at 51% 81%, rgba(74, 232, 255, 0.62), transparent 92px),
    linear-gradient(180deg, #0d258b 0%, #123d9f 47%, #113d9a 66%, #09276d 100%);
}

.hero-shell::before {
  content: "";
  position: absolute;
  inset: 18px -120px 0;
  opacity: 0.9;
  background:
    radial-gradient(ellipse at 48% 86%, rgba(255, 255, 255, 0.82), transparent 16%),
    radial-gradient(circle at 18% 82%, rgba(48, 198, 232, 0.56) 0 18px, transparent 20px),
    radial-gradient(circle at 78% 78%, rgba(31, 197, 236, 0.46) 0 18px, transparent 21px),
    linear-gradient(162deg, transparent 0 7%, rgba(255, 112, 117, 0.64) 13%, rgba(229, 241, 255, 0.85) 21%, rgba(103, 229, 255, 0.46) 28%, transparent 38%),
    linear-gradient(18deg, transparent 0 58%, rgba(95, 232, 255, 0.42) 67%, rgba(238, 248, 255, 0.82) 76%, rgba(255, 105, 108, 0.58) 85%, transparent 96%);
  filter: blur(0.2px);
}

.hero-shell::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 66px;
  background: linear-gradient(180deg, rgba(14, 63, 141, 0), rgba(2, 23, 78, 0.75));
}

.hero-bg-grid {
  position: absolute;
  left: 50%;
  bottom: 28px;
  width: min(820px, calc(100% - 24px));
  height: clamp(82px, 16vw, 176px);
  transform: translateX(-50%);
  opacity: 0.36;
  background:
    linear-gradient(rgba(172, 242, 255, 0.18) 1px, transparent 1px),
    linear-gradient(90deg, rgba(172, 242, 255, 0.18) 1px, transparent 1px);
  background-size: 24px 16px;
  clip-path: polygon(9% 18%, 92% 0, 100% 70%, 83% 100%, 4% 90%, 0 45%);
}

.hero-dna {
  position: absolute;
  bottom: 34px;
  width: 128px;
  height: 80px;
  opacity: 0.68;
  filter: drop-shadow(0 0 8px rgba(118, 239, 255, 0.55));
}

.hero-dna--left {
  left: 50%;
  transform: translateX(-204px);
}

.hero-dna--right {
  right: 50%;
  transform: translateX(207px) scaleX(-1);
}

.hero-copy-wrap {
  position: relative;
  z-index: 2;
  width: min(650px, calc(100% - 40px));
  margin: 0 auto;
  padding-top: 54px;
  text-align: center;
}

.hero-title {
  margin: 0;
  font-size: clamp(24px, 3.9vw, 38px);
  line-height: 1.2;
  font-weight: 900;
  letter-spacing: 0.04em;
  text-shadow: 0 2px 3px rgba(0, 18, 70, 0.28);
}

.hero-subtitle {
  margin: 14px auto 0;
  max-width: 640px;
  font-size: clamp(17px, 3vw, 30px);
  line-height: 1.3;
  font-weight: 900;
  letter-spacing: 0.035em;
  color: rgba(246, 252, 255, 0.96);
  text-shadow: 0 2px 3px rgba(0, 18, 70, 0.28);
}

.hero-search {
  position: relative;
  z-index: 2;
  width: min(540px, calc(100% - 24px));
  margin: 16px auto 0;
  display: grid;
  justify-items: center;
  grid-template-columns: 1fr auto;
  align-items: center;
  column-gap: 10px;
  row-gap: 12px;
}

.hero-search__input-wrap {
  width: 100%;
  height: 42px;
  display: flex;
  align-items: center;
  padding: 0 3px 0 14px;
  border: 2px solid rgba(255, 255, 255, 0.9);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 5px 18px rgba(1, 32, 93, 0.24);
  position: relative;
}

.hero-search__placeholder {
  position: absolute;
  left: 18px;
  color: #9ba6b8;
  font-size: 13px;
  pointer-events: none;
  transition: opacity 0.2s;
}

.hero-search__input-wrap:focus-within .hero-search__placeholder {
  opacity: 0;
}

.hero-search__input {
  width: 100%;
  border: 0;
  height: 100%;
  padding: 0;
  padding-left: 14px;
  outline: none;
  font-size: 13px;
  color: #1c2b44;
}

.hero-search__btn {
  width: 76px;
  height: 32px;
  border: none;
  border-radius: 4px;
  background: #0e55be;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
}

.hero-media {
  position: absolute;
  right: 20px;
  bottom: 14px;
  width: 260px;
  height: 138px;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 10px 30px rgba(0, 16, 53, 0.4);
  background: linear-gradient(140deg, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.04));
  display: none;
}

.hero-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.hero-media__fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.6);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.2em;
}

.news-section {
  background: #f6f9fd;
  padding: clamp(36px, 10vw, 74px) 0 30px;
  min-height: 380px;
}

.news-inner {
  width: min(1130px, calc(100% - 80px));
  margin: 0 auto;
}

.news-headline {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 14px;
}

.news-title {
  position: relative;
  display: flex;
  align-items: flex-end;
  min-height: 35px;
  padding-left: 24px;
  color: #1b3160;
  line-height: 1;
  margin: 0;
}

.news-title::before {
  content: "";
  position: absolute;
  left: 0;
  top: 1px;
  width: 7px;
  height: 31px;
  background: #0e58b9;
  box-shadow: 7px 0 0 rgba(14, 88, 185, 0.12);
}

.news-title small {
  position: absolute;
  left: 25px;
  top: 4px;
  color: #a4adbd;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.news-title strong {
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 0.02em;
  margin: 0;
}

.news-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
  color: #606a7d;
  font-size: 8px;
  font-weight: 700;
  padding-bottom: 8px;
}

.news-tab {
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0;
  cursor: pointer;
}

.news-tab.active {
  color: #0f5ec0;
  font-weight: 800;
}

.news-grid {
  display: grid;
  grid-template-columns: minmax(300px, 1fr) minmax(320px, 1fr);
  gap: 16px;
}

.featured-card {
  position: relative;
  min-height: 232px;
  overflow: hidden;
  background:
    linear-gradient(160deg, rgba(8, 38, 130, 0.95), rgba(19, 110, 207, 0.82)),
    #0a4bad;
  border: 1px solid rgba(9, 56, 152, 0.25);
  box-shadow: 0 2px 4px rgba(4, 38, 91, 0.06);
  border-radius: 3px;
}

.featured-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.12) 1px, transparent 1px),
    linear-gradient(rgba(255, 255, 255, 0.12) 1px, transparent 1px);
  background-size: 34px 24px;
  opacity: 0.2;
}

.featured-card::after {
  content: "";
  position: absolute;
  left: 70px;
  right: 70px;
  bottom: 12px;
  height: 70px;
  border-radius: 6px 6px 0 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.22) 0 10%, transparent 10% 90%, rgba(255, 255, 255, 0.22) 90%),
    linear-gradient(180deg, rgba(250, 253, 255, 0.9), rgba(193, 221, 246, 0.6));
  box-shadow: 0 -55px 70px rgba(245, 251, 255, 0.32), 0 0 0 1px rgba(255, 255, 255, 0.2) inset;
}

.featured-slide {
  position: absolute;
  inset: 0;
}

.featured-fade-enter-active,
.featured-fade-leave-active {
  transition: opacity 0.42s ease, transform 0.42s ease;
}

.featured-fade-enter-from {
  opacity: 0;
  transform: translateX(18px);
}

.featured-fade-leave-to {
  opacity: 0;
  transform: translateX(-18px);
}

.featured-cover {
  position: absolute;
  inset: 0;
}

.featured-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  opacity: 0.84;
}

.featured-card__fallback {
  position: absolute;
  inset: 0;
  background: linear-gradient(160deg, rgba(12, 66, 161, 0.95), rgba(16, 87, 194, 0.8));
}

.featured-chip {
  position: absolute;
  left: 12px;
  top: 12px;
  z-index: 3;
  font-size: 12px;
  color: #fff;
  background: rgba(7, 24, 58, 0.8);
  border-radius: 999px;
  padding: 6px 10px;
  font-weight: 700;
}

.featured-arrow {
  position: absolute;
  z-index: 4;
  top: 51%;
  transform: translateY(-50%);
  width: 34px;
  height: 54px;
  border: 0;
  padding: 0;
  background: transparent;
  color: rgba(255, 255, 255, 0.72);
  font-size: 30px;
  line-height: 1;
  font-family: Georgia, serif;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease;
}

.featured-arrow:hover {
  color: #fff;
  background: rgba(4, 29, 80, 0.16);
}

.featured-arrow--prev {
  left: 8px;
}

.featured-arrow--next {
  right: 8px;
}

.featured-caption-wrap {
  position: absolute;
  z-index: 4;
  left: 0;
  right: 0;
  bottom: 8px;
  padding: 0 15px;
  color: #fff;
}

.featured-title {
  position: relative;
  top: 0;
}

.featured-subtitle {
  margin: 0;
  font-size: 11px;
  font-weight: 800;
}

.featured-heading {
  margin: 4px 0 0;
  font-size: 19px;
  line-height: 1.25;
  font-weight: 900;
  letter-spacing: 0.03em;
  text-shadow: 0 1px 2px rgba(0, 20, 70, 0.62);
}

.featured-date {
  position: relative;
  display: block;
  margin-top: 7px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 800;
  z-index: 3;
}

.featured-summary {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.95);
  font-size: 12px;
  line-height: 1.45;
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.featured-more {
  position: relative;
  z-index: 4;
  display: inline-block;
  margin-top: 10px;
  font-size: 12px;
  color: #d8e8ff;
  text-decoration: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.68);
  padding-bottom: 1px;
}

.featured-dots {
  position: absolute;
  z-index: 5;
  left: 50%;
  bottom: 17px;
  display: flex;
  gap: 11px;
  transform: translateX(-50%);
}

.featured-dot {
  width: 13px;
  height: 13px;
  border: 0;
  border-radius: 999px;
  padding: 0;
  background: rgba(19, 32, 55, 0.86);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: width 0.22s ease, background 0.22s ease;
}

.featured-dot.active {
  width: 24px;
  background: rgba(255, 255, 255, 0.94);
}

.news-list-wrap {
  background: #fff;
  border: 1px solid #e8edf4;
  border-radius: 0;
  padding: 0 0 0 1px;
}

.news-state {
  height: 82px;
  border-bottom: 1px solid var(--line);
  display: grid;
  place-items: center;
  color: #76809a;
  font-size: 13px;
}

.news-state--error {
  color: #9f3f3f;
}

.news-item {
  min-height: 51px;
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr);
  gap: 11px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}

.news-item:last-child {
  border-bottom: 0;
}

.news-item.active {
  background: #f4f8ff;
  box-shadow: inset 3px 0 0 #1764c8;
}

.news-item.active .news-item-thumb {
  border-color: #1764c8;
}

.news-item.active h3 {
  color: #0f55b2;
}

.news-item-thumb {
  height: 40px;
  margin-left: 1px;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background: linear-gradient(135deg, rgba(27, 100, 190, 0.25), rgba(255, 255, 255, 0.2)), #d7e6f6;
  border: 1px solid #d8e3ef;
}

.thumb--room {
  background:
    linear-gradient(90deg, rgba(32, 38, 47, 0.18) 0 32%, transparent 32%),
    linear-gradient(160deg, #f4f1e9 0 36%, #9ea7b1 37% 40%, #ece5dc 41% 100%);
}

.thumb--building {
  background:
    radial-gradient(circle at 50% 70%, rgba(40, 114, 68, 0.35), transparent 32%),
    linear-gradient(160deg, #d6edf6 0 45%, #afc4d2 46% 53%, #eff6fb 54%);
}

.thumb--stage {
  background:
    linear-gradient(180deg, #1964c0 0 56%, #e9f4ff 57% 67%, #0d388e 68%),
    linear-gradient(90deg, #0f4da8, #2e98e2);
}

.thumb--screen {
  background:
    linear-gradient(90deg, transparent 0 12%, rgba(32, 62, 101, 0.22) 13% 16%, transparent 17%),
    linear-gradient(180deg, #d8e9f6 0 33%, #b8cbd8 34% 43%, #e9eff4 44%);
}

.news-item-content h3 {
  margin: 0;
  color: #1d2639;
  font-size: 10px;
  line-height: 1.35;
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.news-item-content h3 a {
  color: inherit;
  text-decoration: none;
}

.news-item-content p {
  margin: 4px 0 0;
  color: #7d8697;
  font-size: 8px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.news-item-tag {
  margin: 0 0 3px;
  font-size: 9px;
  color: #4f5d78;
  font-weight: 700;
}

.news-empty {
  min-height: 51px;
  border-bottom: 1px solid var(--line);
  color: #7d8697;
  font-size: 12px;
  display: grid;
  align-items: center;
  padding: 0 0 0 7px;
}

.news-more-wrap {
  display: flex;
  justify-content: center;
  padding-top: 17px;
}

.news-more {
  width: 60px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #cfd6e2;
  background: #fff;
  color: #7d8796;
  font-size: 8px;
  font-weight: 700;
  text-decoration: none;
}

.news-pagination {
  margin-top: 18px;
  display: flex;
  justify-content: center;
  gap: 10px;
  align-items: center;
  color: #59627b;
  font-size: 11px;
}

.news-pager {
  height: 26px;
  padding: 0 10px;
  border-radius: 5px;
  border: 1px solid #cfd6e2;
  background: #fff;
  color: #6a748a;
}

.news-pager:disabled {
  opacity: 0.6;
}

@media (min-width: 1100px) {
  .hero-copy-wrap {
    padding-top: 90px;
  }

  .hero-title {
    font-size: 38px;
  }

  .hero-subtitle {
    font-size: 30px;
    margin-top: 22px;
  }

  .hero-search {
    width: 540px;
    margin-top: 28px;
    grid-template-columns: 1fr auto;
    gap: 18px;
  }

  .hero-search__input-wrap {
    height: 42px;
    border-radius: 8px;
    padding-left: 24px;
  }

  .hero-search__placeholder {
    left: 24px;
    font-size: 15px;
  }

  .hero-search__btn {
    height: 30px;
    min-width: 76px;
    font-size: 13px;
  }

  .hero-dna {
    width: 205px;
    height: 130px;
    bottom: 54px;
  }

  .hero-dna--left {
    left: calc(50% - 326px);
  }

  .hero-dna--right {
    right: calc(50% - 330px);
  }

  .hero-bg-grid {
    width: 820px;
    height: 176px;
    bottom: 45px;
  }

  .hero-media {
    display: block;
    right: 38px;
    width: 290px;
    height: 154px;
    border-radius: 14px;
    bottom: 32px;
  }

  .news-section {
    padding-top: 76px;
  }

  .news-inner {
    width: min(1130px, calc(100% - 80px));
  }

  .news-headline {
    margin-bottom: 20px;
  }

  .news-title {
    min-height: 57px;
    padding-left: 40px;
  }

  .news-title::before {
    width: 11px;
    height: 50px;
    box-shadow: 12px 0 0 rgba(14, 88, 185, 0.12);
  }

  .news-title small {
    left: 37px;
    top: 6px;
    font-size: 14px;
  }

  .news-title strong {
    font-size: 32px;
  }

  .news-tabs {
    gap: 42px;
    font-size: 13px;
    padding-bottom: 13px;
  }

  .news-grid {
    grid-template-columns: 586px minmax(0, 1fr);
    gap: 26px;
  }

  .featured-card {
    min-height: 370px;
  }

  .featured-arrow {
    width: 44px;
    height: 68px;
    font-size: 48px;
  }

  .featured-arrow--prev {
    left: 14px;
  }

  .featured-arrow--next {
    right: 14px;
  }

  .featured-title {
    top: 24px;
  }

  .featured-heading {
    font-size: 31px;
  }

  .featured-subtitle {
    font-size: 18px;
  }

  .featured-date {
    margin-top: 14px;
    font-size: 21px;
  }

  .featured-caption {
    bottom: 14px;
    padding: 0 24px;
    font-size: 19px;
  }

  .featured-summary {
    font-size: 14px;
    max-width: 90%;
    margin-top: 10px;
    -webkit-line-clamp: 3;
  }

  .featured-card::after {
    left: 116px;
    right: 116px;
    bottom: 20px;
    height: 112px;
  }

  .featured-dots {
    bottom: 29px;
    gap: 17px;
  }

  .featured-dot {
    width: 20px;
    height: 20px;
  }

  .featured-dot.active {
    width: 38px;
  }

  .news-item {
    min-height: 82px;
    grid-template-columns: 112px minmax(0, 1fr);
    gap: 18px;
    padding: 10px 0;
  }

  .news-item-thumb {
    height: 64px;
  }

  .news-item-content h3 {
    font-size: 16px;
  }

  .news-item-content p {
    margin-top: 6px;
    font-size: 13px;
  }

  .news-more {
    width: 96px;
    height: 35px;
    font-size: 13px;
  }
}

@media (max-width: 1100px) {
  .news-tabs {
    font-size: 12px;
  }
}

@media (max-width: 760px) {
  .hero-shell {
    height: 270px;
  }

  .hero-copy-wrap {
    width: min(100% - 26px, 560px);
    padding-top: 38px;
  }

  .hero-title {
    font-size: clamp(22px, 7.8vw, 25px);
  }

  .hero-subtitle {
    font-size: 17px;
    line-height: 1.45;
  }

  .hero-search {
    width: min(330px, 100%);
    margin-top: 20px;
  }

  .hero-search__input-wrap {
    height: 38px;
    padding-right: 3px;
    padding-left: 12px;
  }

  .hero-search__placeholder {
    left: 16px;
    font-size: 11px;
  }

  .hero-search__btn {
    min-width: 60px;
    height: 28px;
    font-size: 12px;
  }

  .hero-dna {
    display: none;
  }

  .hero-bg-grid {
    width: calc(100% - 30px);
  }

  .hero-media {
    display: none;
  }

  .news-section {
    padding-top: 34px;
  }

  .news-inner {
    width: min(620px, calc(100% - 28px));
  }

  .news-headline {
    align-items: flex-start;
    gap: 14px;
    flex-direction: column;
  }

  .news-tabs {
    padding-left: 25px;
    flex-wrap: wrap;
  }

  .news-grid {
    grid-template-columns: 1fr;
  }

  .featured-card {
    min-height: 250px;
  }

  .featured-heading {
    font-size: 21px;
  }

  .featured-date {
    margin-top: 6px;
    font-size: 15px;
  }

  .featured-subtitle {
    font-size: 12px;
  }

  .news-item {
    grid-template-columns: 108px minmax(0, 1fr);
  }

  .news-item-thumb {
    height: 62px;
  }

  .news-item-content h3 {
    font-size: 14px;
  }

  .news-item-content p {
    font-size: 12px;
  }
}

@media (max-width: 430px) {
  .hero-shell {
    height: 295px;
  }

  .hero-search {
    width: min(100% - 24px, 310px);
  }

  .hero-search__input-wrap {
    padding-left: 12px;
  }

  .hero-search__placeholder {
    font-size: 11px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .news-inner {
    width: min(100%, 360px);
  }

  .featured-card {
    min-height: 230px;
  }

  .news-item {
    grid-template-columns: 94px minmax(0, 1fr);
  }

  .news-item-thumb {
    height: 56px;
  }
}
</style>
