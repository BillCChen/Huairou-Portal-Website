<script setup lang="ts">
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, reactive, ref, watch } from "vue";

import { api, adminLoginLockoutsApi, getApiErrorMessage, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

type LogTab = "audit" | "login" | "lockout";

const rows = ref<any[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const activeTab = ref<LogTab>("audit");
const filters = reactive({
  ip: "",
  username: "",
  action: "",
  success: "",
  lockout_type: "",
  active: "true",
});

const shortUserAgent = (value?: string | null) => {
  if (!value) {
    return "-";
  }
  return value.length > 96 ? `${value.slice(0, 96)}...` : value;
};

const successLabel = (value: boolean) => (value ? "成功" : "失败");

const queryParams = () => {
  const params: Record<string, string | number | boolean> = {
    page: page.value,
    page_size: pageSize.value,
  };
  if (filters.ip.trim()) {
    params.ip = filters.ip.trim();
  }
  if (filters.username.trim()) {
    params.username = filters.username.trim();
  }
  if (filters.action.trim()) {
    params.action = filters.action.trim();
  }
  if (activeTab.value === "login" && filters.success) {
    params.success = filters.success === "true";
  }
  if (activeTab.value === "lockout") {
    if (filters.lockout_type.trim()) {
      params.lockout_type = filters.lockout_type.trim();
    }
    if (filters.active) {
      params.active = filters.active === "true";
    }
  }
  return params;
};

const load = async () => {
  loading.value = true;
  try {
    const endpoint = activeTab.value === "audit"
      ? "/admin/audit-logs"
      : activeTab.value === "login"
        ? "/admin/login-logs"
        : "/admin/login-lockouts";
    const data = activeTab.value === "lockout"
      ? await adminLoginLockoutsApi.list(queryParams() as any)
      : await unwrap<{ items: any[]; total: number }>(api.get(endpoint, { params: queryParams() }));
    rows.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
};

const search = () => {
  page.value = 1;
  load();
};

const resetFilters = () => {
  filters.ip = "";
  filters.username = "";
  filters.action = "";
  filters.success = "";
  filters.lockout_type = "";
  filters.active = "true";
  search();
};

const formatDate = (value?: string | null) => {
  if (!value) return "-";
  return value.replace("T", " ").slice(0, 16);
};

const lockoutTypeLabel = (value: string) => {
  const labels: Record<string, string> = {
    account_ip: "账号 + IP",
    ip: "IP 全局",
  };
  return labels[value] || value;
};

const isLockoutActive = (row: any) => {
  if (row.unlocked_at || !row.locked_until) return false;
  return new Date(row.locked_until).getTime() > Date.now();
};

const unlockLockout = async (row: any) => {
  try {
    const result = await ElMessageBox.prompt("请输入解锁原因，20–1000 字。该说明将写入审计日志。", "解锁登录限制", {
      confirmButtonText: "解锁",
      cancelButtonText: "取消",
      inputPlaceholder: "请填写误伤说明、处理依据或管理员确认记录",
      inputType: "textarea",
      inputValidator: (value) => (value || "").trim().length >= 20 && (value || "").trim().length <= 1000,
      inputErrorMessage: "解锁原因需为 20–1000 字",
    });
    await adminLoginLockoutsApi.unlock(row.id, { reason: (result.value || "").trim() });
    ElMessage.success("登录限制已解除");
    await load();
  } catch (error) {
    if (error === "cancel" || error === "close") return;
    ElMessage.error(getApiErrorMessage(error, "解锁失败"));
  }
};

watch(activeTab, search);
onMounted(load);
</script>

<template>
  <AppLayout>
    <div>
      <div style="font-size: 30px; font-weight: 700;">审计日志</div>
      <div style="margin-top: 8px; color: #64748b;">查看后台状态变更、登录记录和请求来源。</div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 12px; margin-top: 24px;">
      <el-input v-model="filters.ip" clearable placeholder="按 IP 筛选" @keyup.enter="search" />
      <el-input v-model="filters.username" clearable placeholder="按账号筛选" @keyup.enter="search" />
      <el-input v-model="filters.action" clearable placeholder="按事件类型筛选" @keyup.enter="search" />
      <el-select v-if="activeTab === 'login'" v-model="filters.success" clearable placeholder="登录结果">
        <el-option label="成功" value="true" />
        <el-option label="失败" value="false" />
      </el-select>
      <el-select v-else-if="activeTab === 'lockout'" v-model="filters.lockout_type" clearable placeholder="锁定类型">
        <el-option label="账号 + IP" value="account_ip" />
        <el-option label="IP 全局" value="ip" />
      </el-select>
      <div v-else />
      <el-select v-if="activeTab === 'lockout'" v-model="filters.active" clearable placeholder="锁定状态">
        <el-option label="生效中" value="true" />
        <el-option label="已解除/过期" value="false" />
      </el-select>
    </div>

    <div style="display: flex; gap: 12px; margin-top: 12px;">
      <el-button type="primary" @click="search">筛选</el-button>
      <el-button @click="resetFilters">重置</el-button>
    </div>

    <el-tabs v-model="activeTab" style="margin-top: 20px;">
      <el-tab-pane label="审计事件" name="audit">
        <el-table :data="rows" v-loading="loading">
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column prop="module" label="模块" min-width="120" />
          <el-table-column prop="action" label="动作" min-width="120" />
          <el-table-column prop="actor_username" label="账号" min-width="140">
            <template #default="{ row }">{{ row.actor_username || row.actor_real_name || row.user_id || "-" }}</template>
          </el-table-column>
          <el-table-column prop="ip_address" label="IP" min-width="140" />
          <el-table-column label="User-Agent" min-width="220">
            <template #default="{ row }">
              <el-tooltip v-if="row.user_agent" :content="row.user_agent" placement="top">
                <span>{{ shortUserAgent(row.user_agent) }}</span>
              </el-tooltip>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="180" />
          <el-table-column prop="method" label="方法" width="90" />
          <el-table-column prop="result" label="结果" width="100" />
          <el-table-column prop="object_type" label="对象类型" min-width="120" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="登录记录" name="login">
        <el-table :data="rows" v-loading="loading">
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column prop="username" label="账号" min-width="160" />
          <el-table-column prop="login_method" label="登录方式" min-width="120" />
          <el-table-column label="结果" width="100">
            <template #default="{ row }">{{ successLabel(row.success) }}</template>
          </el-table-column>
          <el-table-column prop="failure_reason" label="失败原因" min-width="140" />
          <el-table-column prop="ip_address" label="IP" min-width="140" />
          <el-table-column label="User-Agent" min-width="220">
            <template #default="{ row }">
              <el-tooltip v-if="row.user_agent" :content="row.user_agent" placement="top">
                <span>{{ shortUserAgent(row.user_agent) }}</span>
              </el-tooltip>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="path" label="路径" min-width="180" />
          <el-table-column prop="method" label="方法" width="90" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="登录限制" name="lockout">
        <el-table :data="rows" v-loading="loading">
          <el-table-column prop="created_at" label="创建时间" min-width="165">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="类型" min-width="110">
            <template #default="{ row }">{{ lockoutTypeLabel(row.lockout_type) }}</template>
          </el-table-column>
          <el-table-column prop="normalized_identifier" label="账号标识" min-width="160">
            <template #default="{ row }">{{ row.normalized_identifier || "-" }}</template>
          </el-table-column>
          <el-table-column prop="ip_address" label="IP" min-width="140" />
          <el-table-column prop="failure_count" label="失败次数" width="100" />
          <el-table-column prop="locked_until" label="锁定至" min-width="165">
            <template #default="{ row }">{{ formatDate(row.locked_until) }}</template>
          </el-table-column>
          <el-table-column prop="reason" label="原因" min-width="180" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="isLockoutActive(row) ? 'danger' : 'info'" effect="plain">
                {{ isLockoutActive(row) ? "生效中" : "已解除/过期" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button v-if="isLockoutActive(row)" size="small" type="primary" plain @click="unlockLockout(row)">
                解锁
              </el-button>
              <span v-else>-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <div style="display: flex; justify-content: flex-end; margin-top: 20px;">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        layout="prev, pager, next, total"
        :total="total"
        @current-change="load"
      />
    </div>
  </AppLayout>
</template>
