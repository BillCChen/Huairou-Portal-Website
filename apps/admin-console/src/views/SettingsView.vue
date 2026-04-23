<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const settings = ref<any[]>([]);

const load = async () => {
  settings.value = await unwrap<any[]>(api.get("/admin/settings"));
};

const save = async (row: any) => {
  await unwrap(api.put(`/admin/settings/${row.setting_key}`, { setting_value: row.setting_value, group_name: row.group_name }));
  ElMessage.success("设置已保存");
};

const updateJsonValue = (row: any, value: string) => {
  try {
    row.setting_value = JSON.parse(value);
  } catch {
    ElMessage.error("JSON 格式无效");
  }
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div>
      <div style="font-size: 30px; font-weight: 700;">站点设置</div>
      <div style="margin-top: 8px; color: #64748b;">首页统计卡片、快速入口、页脚和联系方式统一通过配置管理。</div>
    </div>
    <el-table :data="settings" style="margin-top: 24px;">
      <el-table-column prop="setting_key" label="Key" min-width="220" />
      <el-table-column prop="group_name" label="Group" width="140" />
      <el-table-column label="Value" min-width="420">
        <template #default="{ row }">
          <el-input
            :model-value="JSON.stringify(row.setting_value, null, 2)"
            type="textarea"
            :rows="4"
            @change="(value: string) => updateJsonValue(row, value)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button type="primary" size="small" @click="save(row)">保存</el-button>
        </template>
      </el-table-column>
    </el-table>
  </AppLayout>
</template>
