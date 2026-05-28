<script setup lang="ts">
const route = useRoute();
const loading = ref(false);
const success = ref(false);
const errorMessage = ref("");
let redirectTimer: ReturnType<typeof setTimeout> | undefined;

const form = reactive({
  newPassword: "",
  confirmPassword: "",
});

const token = computed(() => {
  const value = route.query.token;
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
});

const hasToken = computed(() => token.value.trim().length > 0);

const invalidLinkMessage = "重置链接无效或已过期，请重新申请。";

const submit = async () => {
  if (!hasToken.value) {
    errorMessage.value = "链接无效或缺少 token";
    return;
  }
  if (form.newPassword.length < 8) {
    errorMessage.value = "新密码长度不能少于 8 位";
    return;
  }
  if (form.newPassword !== form.confirmPassword) {
    errorMessage.value = "两次输入的密码不一致";
    return;
  }

  loading.value = true;
  success.value = false;
  errorMessage.value = "";
  try {
    await confirmPasswordReset(token.value, form.newPassword);
    success.value = true;
    form.newPassword = "";
    form.confirmPassword = "";
    redirectTimer = setTimeout(() => {
      navigateTo("/login");
    }, 1200);
  } catch (error: unknown) {
    const message = getPortalErrorMessage(error, invalidLinkMessage);
    errorMessage.value = /token|expired|invalid|重置链接|过期/i.test(message)
      ? invalidLinkMessage
      : message;
  } finally {
    loading.value = false;
  }
};

onBeforeUnmount(() => {
  if (redirectTimer) {
    clearTimeout(redirectTimer);
  }
});

useSeoMeta({
  title: "重置密码",
  description: "通过邮件链接设置新密码。",
});
</script>

<template>
  <div class="container list-page">
    <div class="card" style="max-width: 720px; margin: 0 auto; padding: 30px;">
      <div class="badge">Password Reset</div>
      <h1 class="section-title" style="font-size: 36px; margin-top: 18px;">重置密码</h1>
      <p class="section-desc">请设置新的账号密码。链接不可重复使用。</p>

      <div
        v-if="!hasToken"
        style="margin-top: 18px; color: #b91c1c; background: #fff1f2; border: 1px solid #fecdd3; border-radius: 14px; padding: 14px 16px;"
      >
        链接无效或缺少 token。
      </div>

      <form v-else style="margin-top: 24px;" @submit.prevent="submit">
        <div class="form-grid">
          <label>
            <div style="margin-bottom: 8px;">新密码</div>
            <input
              v-model="form.newPassword"
              class="input"
              type="password"
              autocomplete="new-password"
              :disabled="loading || success"
            />
          </label>
          <label>
            <div style="margin-bottom: 8px;">确认新密码</div>
            <input
              v-model="form.confirmPassword"
              class="input"
              type="password"
              autocomplete="new-password"
              :disabled="loading || success"
            />
          </label>
        </div>

        <div style="display: flex; gap: 12px; margin-top: 22px; flex-wrap: wrap;">
          <button class="button" type="submit" :disabled="loading || success">
            {{ loading ? "提交中" : "确认重置" }}
          </button>
          <NuxtLink class="button secondary" to="/login">返回登录</NuxtLink>
        </div>
      </form>

      <div
        v-if="success"
        style="margin-top: 18px; color: #0f766e; background: #ecfeff; border: 1px solid #99f6e4; border-radius: 14px; padding: 14px 16px;"
      >
        密码已重置，即将返回登录页。
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
