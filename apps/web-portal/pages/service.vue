<script setup lang="ts">
const { data: page } = await useAsyncData("service-page", () => usePortalApi<any>("/public/pages/service"));
const success = ref("");
const errorMessage = ref("");
const form = reactive({
  type: "consultation",
  subject: "",
  contact_name: "",
  contact_mobile: "",
  contact_email: "",
  organization: "",
  content: "",
});

const submit = async () => {
  success.value = "";
  errorMessage.value = "";
  try {
    await usePortalApi("/public/inquiries", { method: "POST", body: form });
    success.value = "咨询已提交，后台线索池可查看该记录。";
    form.subject = "";
    form.contact_name = "";
    form.contact_mobile = "";
    form.contact_email = "";
    form.organization = "";
    form.content = "";
  } catch (error: any) {
    errorMessage.value = error?.data?.message || error?.message || "提交失败";
  }
};
</script>

<template>
  <div class="container list-page">
    <div class="badge">Service Entry</div>
    <h1 class="section-title" style="margin-top: 18px;">在线服务</h1>
    <p class="section-desc">当前按轻量模式实现在线咨询表单，并为服务预约、资料下载保留扩展位。</p>
    <div class="card-grid" style="margin-top: 24px;">
      <section class="card" style="grid-column: span 5; padding: 26px;">
        <div class="rich-content" v-html="page?.content_html" />
        <div class="card" style="margin-top: 20px; padding: 18px; background: #f8fbff;">
          <div style="font-size: 18px; font-weight: 700;">后续扩展位</div>
          <ul style="margin: 12px 0 0; color: var(--muted); line-height: 1.8;">
            <li>服务预约流程</li>
            <li>资料下载权限控制</li>
            <li>活动报名与进度查询</li>
          </ul>
        </div>
      </section>
      <section class="card" style="grid-column: span 7; padding: 26px;">
        <div style="font-size: 28px; font-weight: 700;">在线咨询</div>
        <div class="form-grid" style="margin-top: 18px;">
          <label>
            <div style="margin-bottom: 8px;">咨询主题</div>
            <input v-model="form.subject" class="input" />
          </label>
          <label>
            <div style="margin-bottom: 8px;">联系人</div>
            <input v-model="form.contact_name" class="input" />
          </label>
          <label>
            <div style="margin-bottom: 8px;">手机号</div>
            <input v-model="form.contact_mobile" class="input" />
          </label>
          <label>
            <div style="margin-bottom: 8px;">邮箱</div>
            <input v-model="form.contact_email" class="input" />
          </label>
          <label style="grid-column: 1 / -1;">
            <div style="margin-bottom: 8px;">单位</div>
            <input v-model="form.organization" class="input" />
          </label>
          <label style="grid-column: 1 / -1;">
            <div style="margin-bottom: 8px;">咨询内容</div>
            <textarea v-model="form.content" class="textarea"></textarea>
          </label>
        </div>
        <button class="button" style="margin-top: 20px;" @click="submit">提交咨询</button>
        <div v-if="success" style="margin-top: 16px; color: #0f766e;">{{ success }}</div>
        <div v-if="errorMessage" style="margin-top: 16px; color: #b91c1c;">{{ errorMessage }}</div>
      </section>
    </div>
  </div>
</template>
