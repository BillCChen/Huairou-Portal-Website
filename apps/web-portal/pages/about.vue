<script setup lang="ts">
const [{ data: about }, { data: leaders }, { data: settings }] = await Promise.all([
  useAsyncData("page-about", () => usePortalApi<any>("/public/pages/about")),
  useAsyncData("leaders", () => usePortalApi<any[]>("/public/leaders")),
  useSiteSettings(),
]);

const profile = computed(() => settings.value?.site_profile || {});

useSeoMeta({
  title: () => `关于我们 | ${profile.value.site_name || "门户网站"}`,
  description: () => about.value?.seo_description || "机构介绍、领导团队与联系方式。",
});
</script>

<template>
  <div class="container list-page">
    <section class="list-page__hero">
      <div class="badge">About Us</div>
      <h1 class="section-title" style="margin-top: 18px;">{{ about?.title || "关于我们" }}</h1>
      <p class="section-desc">门户网站通过单页内容管理承接机构介绍、治理结构、领导团队与联系方式。</p>
    </section>

    <section class="card" style="padding: 30px;">
      <div class="rich-content" v-html="about?.content_html" />
      <div v-if="about?.blocks?.length" class="card-grid" style="margin-top: 26px;">
        <div v-for="block in about.blocks" :key="block.title" class="card" style="grid-column: span 6; padding: 22px; background: #f8fbff;">
          <div class="badge">{{ block.type }}</div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 14px;">{{ block.title }}</div>
          <div style="margin-top: 12px; color: var(--muted); line-height: 1.8;">{{ block.content }}</div>
        </div>
      </div>
    </section>

    <section v-if="(leaders || []).length" class="section" style="padding-bottom: 24px;">
      <div class="section-title" style="font-size: 28px;">领导团队</div>
      <div class="card-grid" style="margin-top: 18px;">
        <article v-for="leader in leaders || []" :key="leader.id" class="card" style="grid-column: span 4; padding: 22px;">
          <div style="width: 72px; height: 72px; border-radius: 24px; background: linear-gradient(135deg, #0f5b78, #2a7d6f);"></div>
          <div style="font-size: 24px; font-weight: 700; margin-top: 18px;">{{ leader.name }}</div>
          <div style="margin-top: 6px; color: var(--accent); font-weight: 600;">{{ leader.title }}</div>
          <div style="margin-top: 14px; color: var(--muted); line-height: 1.8;">{{ leader.intro }}</div>
        </article>
      </div>
    </section>

    <section class="card" style="padding: 28px;">
      <div class="section-title" style="font-size: 28px;">联系我们</div>
      <div class="card-grid" style="margin-top: 18px;">
        <div class="card" style="grid-column: span 4; padding: 20px; background: #f8fbff;">
          <div style="color: var(--muted);">地址</div>
          <div style="margin-top: 10px; font-weight: 600;">{{ profile.address }}</div>
        </div>
        <div class="card" style="grid-column: span 4; padding: 20px; background: #f8fbff;">
          <div style="color: var(--muted);">电话</div>
          <div style="margin-top: 10px; font-weight: 600;">{{ profile.contact_phone }}</div>
        </div>
        <div class="card" style="grid-column: span 4; padding: 20px; background: #f8fbff;">
          <div style="color: var(--muted);">邮箱</div>
          <div style="margin-top: 10px; font-weight: 600;">{{ profile.contact_email }}</div>
        </div>
      </div>
    </section>
  </div>
</template>
