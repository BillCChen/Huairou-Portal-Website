<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const rows = ref<any[]>([]);
const loading = ref(false);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);

const load = async () => {
  loading.value = true;
  try {
    const data = await unwrap<{ items: any[]; total: number }>(api.get("/admin/audit-logs", {
      params: {
        page: page.value,
        page_size: pageSize.value,
      },
    }));
    rows.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div>
      <div style="font-size: 30px; font-weight: 700;">审计日志</div>
      <div style="margin-top: 8px; color: #64748b;">查看后台状态变更记录和操作者信息。</div>
    </div>

    <el-table :data="rows" v-loading="loading" style="margin-top: 24px;">
      <el-table-column prop="created_at" label="创建时间" min-width="180" />
      <el-table-column prop="module" label="模块" min-width="140" />
      <el-table-column prop="action" label="动作" width="120" />
      <el-table-column prop="object_type" label="对象类型" min-width="140" />
      <el-table-column prop="user_id" label="用户 ID" width="100" />
    </el-table>

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
