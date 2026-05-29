<script setup lang="ts">
import { onMounted, reactive, ref, watch } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

type LogTab = "audit" | "login";

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
  return params;
};

const load = async () => {
  loading.value = true;
  try {
    const endpoint = activeTab.value === "audit" ? "/admin/audit-logs" : "/admin/login-logs";
    const data = await unwrap<{ items: any[]; total: number }>(api.get(endpoint, { params: queryParams() }));
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
  search();
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
      <div v-else />
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
