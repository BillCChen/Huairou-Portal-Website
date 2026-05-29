<script setup lang="ts">
const me = ref<PortalUser | null>(null);
const errorMessage = ref("");

onMounted(async () => {
  if (!getPortalToken()) {
    await navigateTo("/login");
    return;
  }
  try {
    me.value = await getCurrentPortalUser();
  } catch (error: any) {
    if ((error?.statusCode || error?.status) === 401) {
      clearPortalSession();
      await navigateTo("/login");
      return;
    }
    errorMessage.value = error?.data?.message || error?.data?.detail || error?.message || "无法获取用户信息";
  }
});

const logout = async () => {
  clearPortalSession();
  await navigateTo("/");
};

const statusMap: Record<string, string> = {
  active: "已启用",
  pending: "待审核",
  disabled: "已禁用",
  rejected: "已驳回",
};

const roleMap: Record<string, string> = {
  super_admin: "超级管理员",
  content_admin: "内容管理员",
  auditor: "审核员",
  institute_editor: "机构用户",
  registered_user: "注册用户",
};

const roleLabel = computed(() => {
  if (!me.value) {
    return "-";
  }
  return me.value.role_name || (me.value.role_code ? roleMap[me.value.role_code] || me.value.role_code : "-");
});

const statusLabel = computed(() => {
  const status = me.value?.status;
  return status ? statusMap[status] || status : "-";
});

useSeoMeta({
  title: "个人中心",
  description: "查看当前登录用户的基础资料与审核状态。",
});
</script>

<template>
  <div class="container list-page">
    <div class="card" style="max-width: 760px; margin: 0 auto; padding: 30px;">
      <div class="badge">User Center</div>
      <h1 class="section-title" style="font-size: 36px; margin-top: 18px;">用户中心</h1>
      <p class="section-desc">当前只承接基础账号信息查看，不扩展编辑、消息中心或个人工作台。</p>
      <div v-if="me" class="card" style="margin-top: 24px; padding: 22px; background: #f8fbff;">
        <div style="display: grid; gap: 12px;">
          <div><strong>用户名：</strong>{{ me.username || "-" }}</div>
          <div><strong>真实姓名：</strong>{{ me.real_name || "-" }}</div>
          <div><strong>邮箱：</strong>{{ me.email || "-" }}</div>
          <div><strong>手机号：</strong>{{ me.mobile || "-" }}</div>
          <div><strong>单位：</strong>{{ me.organization || "-" }}</div>
          <div><strong>角色：</strong>{{ roleLabel }}</div>
          <div>
            <strong>账号状态：</strong>
            <span
              style="display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; background: #fee2e2; color: #b91c1c; font-size: 13px;"
              :style="me.status === 'active' ? 'background:#dcfce7;color:#166534;' : me.status === 'pending' ? 'background:#fef3c7;color:#92400e;' : ''"
            >
              {{ statusLabel }}
            </span>
          </div>
        </div>
        <button class="button secondary" style="margin-top: 20px;" @click="logout">退出登录</button>
      </div>
      <div v-else-if="errorMessage" style="margin-top: 18px; color: #b91c1c;">{{ errorMessage }}</div>
      <div v-else style="margin-top: 18px; color: var(--muted);">正在加载用户信息。</div>
    </div>
  </div>
</template>
