<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const rows = ref<any[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);

const form = reactive({
  name: "",
  slug: "",
  intro: "",
  directionsText: "[]",
  status: "hidden",
  sort_order: 0,
});

const slugify = (value: string) => value
  .trim()
  .toLowerCase()
  .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
  .replace(/^-+|-+$/g, "");

const load = async () => {
  loading.value = true;
  try {
    rows.value = await unwrap<any[]>(api.get("/admin/institutes"));
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  form.name = "";
  form.slug = "";
  form.intro = "";
  form.directionsText = "[]";
  form.status = "hidden";
  form.sort_order = 0;
};

const openCreate = () => {
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
};

const openEdit = (row: any) => {
  editingId.value = row.id;
  form.name = row.name;
  form.slug = row.slug;
  form.intro = row.intro || "";
  form.directionsText = JSON.stringify(row.directions || [], null, 2);
  form.status = row.status || "hidden";
  form.sort_order = row.sort_order || 0;
  dialogVisible.value = true;
};

const submit = async () => {
  let directions: Array<Record<string, unknown>> = [];
  try {
    directions = JSON.parse(form.directionsText || "[]");
  } catch {
    ElMessage.error("方向配置格式无效");
    return;
  }

  const payload = {
    name: form.name,
    slug: form.slug || slugify(form.name),
    intro: form.intro,
    directions,
    status: form.status,
    sort_order: form.sort_order,
    contact: {},
    related_article_ids: [],
    related_case_ids: [],
    cover_file_id: null,
  };

  if (editingId.value) {
    await unwrap(api.put(`/admin/institutes/${editingId.value}`, payload));
  } else {
    await unwrap(api.post("/admin/institutes", payload));
  }
  ElMessage.success("保存成功");
  dialogVisible.value = false;
  editingId.value = null;
  resetForm();
  await load();
};

const instituteStatusText = (status: string) => {
  const map: Record<string, string> = {
    published: "已发布",
    hidden: "隐藏",
  };
  return map[status] || status;
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
      <div>
        <div style="font-size: 30px; font-weight: 700;">研究所管理</div>
        <div style="margin-top: 8px; color: #64748b;">维护研究所简介、研究方向、排序和发布状态。</div>
      </div>
      <el-button type="primary" @click="openCreate">新增内容</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" style="margin-top: 24px;">
      <el-table-column prop="name" label="名称" min-width="220" />
      <el-table-column prop="slug" label="标识" min-width="180" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          {{ instituteStatusText(row.status) }}
        </template>
      </el-table-column>
      <el-table-column prop="sort_order" label="排序" width="100" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑内容' : '新建内容'" width="760">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="标识">
          <el-input v-model="form.slug" />
        </el-form-item>
        <el-form-item label="简介">
          <el-input v-model="form.intro" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="方向配置">
          <el-input v-model="form.directionsText" type="textarea" :rows="8" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%;">
            <el-option label="隐藏" value="hidden" />
            <el-option label="已发布" value="published" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>
