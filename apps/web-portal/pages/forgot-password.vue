<script setup lang="ts">
const loading = ref(false);
const submitted = ref(false);
const errorMessage = ref("");

const form = reactive({
  emailOrUsername: "",
});

const safeSuccessMessage = "如果账号存在并已配置邮箱，系统将发送密码重置邮件，请查收。";

const submit = async () => {
  const identifier = form.emailOrUsername.trim();
  if (!identifier) {
    errorMessage.value = "请输入邮箱或用户名";
    return;
  }

  loading.value = true;
  errorMessage.value = "";
  submitted.value = false;
  try {
    await requestPasswordReset(identifier);
    submitted.value = true;
  } catch (error: unknown) {
    errorMessage.value = getPortalErrorMessage(error, "密码重置请求暂时无法提交，请稍后重试");
  } finally {
    loading.value = false;
  }
};

useSeoMeta({
  title: "找回密码",
  description: "通过邮箱接收密码重置说明。",
});
</script>

<template>
  <div class="container list-page">
    <div class="card" style="max-width: 720px; margin: 0 auto; padding: 30px;">
      <div class="badge">Password Recovery</div>
      <h1 class="section-title" style="font-size: 36px; margin-top: 18px;">找回密码</h1>
      <p class="section-desc">输入邮箱或用户名后，系统将按安全流程处理密码重置请求。</p>

      <form style="margin-top: 24px;" @submit.prevent="submit">
        <div class="form-grid">
          <label>
            <div style="margin-bottom: 8px;">邮箱或用户名</div>
            <input
              v-model="form.emailOrUsername"
              class="input"
              autocomplete="username"
              :disabled="loading"
            />
          </label>
        </div>

        <div style="display: flex; gap: 12px; margin-top: 22px; flex-wrap: wrap;">
          <button class="button" type="submit" :disabled="loading">
            {{ loading ? "提交中" : "发送重置邮件" }}
          </button>
          <NuxtLink class="button secondary" to="/login">返回登录</NuxtLink>
        </div>
      </form>

      <div
        v-if="submitted"
        style="margin-top: 18px; color: #0f766e; background: #ecfeff; border: 1px solid #99f6e4; border-radius: 14px; padding: 14px 16px;"
      >
        {{ safeSuccessMessage }}
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
