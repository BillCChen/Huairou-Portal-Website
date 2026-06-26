<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, reactive } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "../stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const form = reactive({
  username: "",
  password: "",
});
const expiredMessage = computed(() => (route.query.reason === "expired" ? "登录已过期，请重新登录。" : ""));

const submit = async () => {
  try {
    await auth.login(form.username, form.password);
    ElMessage.success("登录成功");
    router.push("/dashboard");
  } catch (error) {
    ElMessage.error("登录失败，请检查账号或密码");
    console.error(error);
  }
};
</script>

<template>
  <div style="min-height: 100vh; display: grid; place-items: center; padding: 32px;">
    <div class="content-card" style="width: min(460px, 100%); padding: 36px;">
      <div style="font-size: 28px; font-weight: 700;">门户网站管理后台</div>
      <div style="margin-top: 8px; color: #64748b;">请使用管理员账号登录。</div>
      <el-alert
        v-if="expiredMessage"
        :title="expiredMessage"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top: 20px;"
      />
      <el-form style="margin-top: 28px;" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%;" @click="submit">登录后台</el-button>
      </el-form>
    </div>
  </div>
</template>
