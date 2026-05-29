<script setup lang="ts">
const loading = ref(false);
const errorMessage = ref("");

const form = reactive({
  real_name: "",
  organization: "",
  mobile: "",
  email: "",
  expertise: "",
  password: "",
});

const submit = async () => {
  loading.value = true;
  errorMessage.value = "";
  try {
    if (!isPasswordPolicyCompliant(form.password)) {
      errorMessage.value = passwordPolicyHint;
      return;
    }
    await usePortalApi<{ status: string; user_id: number }>("/auth/register", {
      method: "POST",
      body: form,
    });
    await navigateTo("/?registered=pending");
  } catch (error: any) {
    errorMessage.value = error?.data?.message || error?.data?.detail || error?.message || "注册失败";
  } finally {
    loading.value = false;
  }
};

useSeoMeta({
  title: "注册",
  description: "个人用户注册后进入待审核状态。",
});
</script>

<template>
  <div class="container list-page">
    <div class="card" style="max-width: 820px; margin: 0 auto; padding: 30px;">
      <div class="badge">Registration Review</div>
      <h1 class="section-title" style="font-size: 36px; margin-top: 18px;">个人用户注册</h1>
      <p class="section-desc">注册表单按文档中的最小字段集实现，提交后默认进入待审核状态。</p>
      <div class="form-grid" style="margin-top: 24px;">
        <label>
          <div style="margin-bottom: 8px;">姓名</div>
          <input v-model="form.real_name" class="input" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">单位</div>
          <input v-model="form.organization" class="input" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">手机号</div>
          <input v-model="form.mobile" class="input" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">邮箱</div>
          <input v-model="form.email" class="input" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">专业领域</div>
          <input v-model="form.expertise" class="input" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">密码</div>
          <input v-model="form.password" class="input" type="password" />
          <div style="margin-top: 8px; color: #64748b; font-size: 13px; line-height: 1.5;">{{ passwordPolicyHint }}</div>
        </label>
      </div>
      <div style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap;">
        <button class="button" :disabled="loading" @click="submit">提交注册</button>
        <NuxtLink class="button secondary" to="/login">返回登录</NuxtLink>
      </div>
      <div v-if="errorMessage" style="margin-top: 18px; color: #b91c1c;">{{ errorMessage }}</div>
    </div>
  </div>
</template>
