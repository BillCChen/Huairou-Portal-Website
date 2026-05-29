<script setup lang="ts">
const tab = ref<"password" | "sms">("password");
const loading = ref(false);
const errorMessage = ref("");

const form = reactive({
  username: "",
  password: "",
  mobile: "",
  code: "",
});

const submit = async () => {
  loading.value = true;
  errorMessage.value = "";
  try {
    const path = tab.value === "password" ? "/auth/login/password" : "/auth/login/sms";
    const payload = tab.value === "password"
      ? { username: form.username, password: form.password }
      : { mobile: form.mobile, code: form.code };
    const response = await usePortalApi<{ access_token: string; user: PortalUser }>(path, {
      method: "POST",
      body: payload,
    });
    setPortalSession(response.access_token, response.user);
    await navigateTo("/profile");
  } catch (error: unknown) {
    errorMessage.value = getPortalErrorMessage(error, "登录失败");
  } finally {
    loading.value = false;
  }
};

useSeoMeta({
  title: "登录",
  description: "用户登录入口。",
});
</script>

<template>
  <div class="container list-page">
    <div class="card" style="max-width: 720px; margin: 0 auto; padding: 30px;">
      <div class="badge">Authentication</div>
      <h1 class="section-title" style="font-size: 36px; margin-top: 18px;">用户登录</h1>
      <p class="section-desc">请输入账号凭据登录门户服务。</p>
      <div style="display: flex; gap: 12px; margin-top: 24px; flex-wrap: wrap;">
        <button class="button" :class="{ secondary: tab !== 'password' }" @click="tab = 'password'">账号密码登录</button>
        <button class="button" :class="{ secondary: tab !== 'sms' }" @click="tab = 'sms'">手机号验证码登录</button>
      </div>
      <div class="form-grid" style="margin-top: 24px;">
        <label v-if="tab === 'password'">
          <div style="margin-bottom: 8px;">Username</div>
          <input v-model="form.username" class="input" />
        </label>
        <label v-if="tab === 'password'">
          <div style="margin-bottom: 8px;">Password</div>
          <input v-model="form.password" class="input" type="password" />
        </label>
        <label v-if="tab === 'sms'">
          <div style="margin-bottom: 8px;">Mobile</div>
          <input v-model="form.mobile" class="input" />
        </label>
        <label v-if="tab === 'sms'">
          <div style="margin-bottom: 8px;">Code</div>
          <input v-model="form.code" class="input" />
        </label>
      </div>
      <div style="display: flex; gap: 12px; margin-top: 22px; flex-wrap: wrap;">
        <button class="button" :disabled="loading" @click="submit">提交登录</button>
        <NuxtLink class="button secondary" to="/register">新用户注册</NuxtLink>
        <NuxtLink v-if="tab === 'password'" class="button secondary" to="/forgot-password">忘记密码？</NuxtLink>
      </div>
      <div
        v-if="errorMessage"
        style="margin-top: 18px; color: #b91c1c; background: #fff1f2; border: 1px solid #fecdd3; border-radius: 14px; padding: 14px 16px;"
      >
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>
