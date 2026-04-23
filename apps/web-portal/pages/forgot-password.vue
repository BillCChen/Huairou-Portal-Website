<script setup lang="ts">
const loading = ref(false);
const sending = ref(false);
const errorMessage = ref("");

const form = reactive({
  mobile: "",
  code: "",
  new_password: "",
  confirm_password: "",
});

const sendCode = async () => {
  sending.value = true;
  errorMessage.value = "";
  try {
    await usePortalApi("/auth/sms-send", {
      method: "POST",
      body: { mobile: form.mobile },
    });
  } catch (error: any) {
    errorMessage.value = error?.data?.message || error?.data?.detail || error?.message || "验证码发送失败";
  } finally {
    sending.value = false;
  }
};

const submit = async () => {
  if (form.new_password.length < 8) {
    errorMessage.value = "新密码长度不能少于 8 位";
    return;
  }
  if (form.new_password !== form.confirm_password) {
    errorMessage.value = "两次输入的密码不一致";
    return;
  }
  loading.value = true;
  errorMessage.value = "";
  try {
    await usePortalApi("/auth/reset-password", {
      method: "POST",
      body: {
        mobile: form.mobile,
        code: form.code,
        new_password: form.new_password,
      },
    });
    await navigateTo("/login");
  } catch (error: any) {
    errorMessage.value = error?.data?.message || error?.data?.detail || error?.message || "密码重置失败";
  } finally {
    loading.value = false;
  }
};

useSeoMeta({
  title: "找回密码",
  description: "通过手机号验证码重置用户密码。",
});
</script>

<template>
  <div class="container list-page">
    <div class="card" style="max-width: 760px; margin: 0 auto; padding: 30px;">
      <div class="badge">Password Recovery</div>
      <h1 class="section-title" style="font-size: 36px; margin-top: 18px;">找回密码</h1>
      <p class="section-desc">请输入手机号、验证码和新密码完成密码重置。</p>
      <div class="form-grid" style="margin-top: 24px;">
        <label>
          <div style="margin-bottom: 8px;">手机号</div>
          <input v-model="form.mobile" class="input" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">验证码</div>
          <div style="display: flex; gap: 12px;">
            <input v-model="form.code" class="input" style="flex: 1 1 auto;" />
            <button class="button secondary" type="button" :disabled="sending || !form.mobile" @click="sendCode">
              {{ sending ? "发送中" : "获取验证码" }}
            </button>
          </div>
        </label>
        <label>
          <div style="margin-bottom: 8px;">新密码</div>
          <input v-model="form.new_password" class="input" type="password" />
        </label>
        <label>
          <div style="margin-bottom: 8px;">确认密码</div>
          <input v-model="form.confirm_password" class="input" type="password" />
        </label>
      </div>
      <div style="display: flex; gap: 12px; margin-top: 22px; flex-wrap: wrap;">
        <button class="button" :disabled="loading" @click="submit">提交重置</button>
        <NuxtLink class="button secondary" to="/login">返回登录</NuxtLink>
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
