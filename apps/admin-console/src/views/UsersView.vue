<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const users = ref<any[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const statusFilter = ref("");

const load = async () => {
  const data = await unwrap<{ items: any[]; total: number; page: number; page_size: number }>(api.get("/admin/users", {
    params: {
      page: page.value,
      page_size: pageSize.value,
      status: statusFilter.value || undefined,
    },
  }));
  users.value = data.items;
  total.value = data.total;
};

const approve = async (id: number) => {
  await unwrap(api.post(`/admin/users/${id}/approve`, { review_comment: "管理员审批通过" }));
  ElMessage.success("审核通过");
  await load();
};

const statusLabel = (status: string) => {
  const labelMap: Record<string, string> = {
    pending: "待审核",
    active: "已启用",
    disabled: "已禁用",
    inactive: "未启用",
  };
  return labelMap[status] || status;
};

const handleFilterChange = async () => {
  page.value = 1;
  await load();
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div>
      <div style="font-size: 30px; font-weight: 700;">用户审核</div>
      <div style="margin-top: 8px; color: #64748b;">个人注册用户默认进入待审核状态，审核通过后才能登录。</div>
    </div>
    <div style="display: flex; justify-content: flex-end; margin-top: 20px;">
      <el-select v-model="statusFilter" placeholder="状态" style="width: 180px;" @change="handleFilterChange">
        <el-option label="全部" value="" />
        <el-option label="待审核" value="pending" />
        <el-option label="已启用" value="active" />
        <el-option label="已禁用" value="disabled" />
      </el-select>
    </div>
    <el-table :data="users" style="margin-top: 24px;">
      <el-table-column prop="real_name" label="姓名" min-width="160" />
      <el-table-column prop="organization" label="单位" min-width="220" />
      <el-table-column prop="mobile" label="手机号" min-width="160" />
      <el-table-column prop="expertise" label="专业领域" min-width="180" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          {{ statusLabel(row.status) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" type="primary" size="small" @click="approve(row.id)">
            审核通过
          </el-button>
        </template>
      </el-table-column>
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
