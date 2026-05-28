<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref, watch } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const rows = ref<any[]>([]);
const tagRows = ref<any[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const slugTouched = ref(false);
const tagDialogVisible = ref(false);
const tagEditingId = ref<number | null>(null);
const tagSlugTouched = ref(false);

const form = reactive({
  name: "",
  slug: "",
  type: "article",
  parent_id: null as number | null,
  sort_order: 0,
  enabled: true,
});

const tagForm = reactive({
  name: "",
  slug: "",
  type: "content",
  color: "",
  enabled: true,
});

const slugify = (value: string) => value
  .trim()
  .toLowerCase()
  .replace(/[^\p{Letter}\p{Number}]+/gu, "-")
  .replace(/^-+|-+$/g, "");

watch(() => form.name, (value) => {
  if (!slugTouched.value) {
    form.slug = slugify(value);
  }
});

watch(() => tagForm.name, (value) => {
  if (!tagSlugTouched.value) {
    tagForm.slug = slugify(value);
  }
});

const load = async () => {
  loading.value = true;
  try {
    const [categoryData, tagData] = await Promise.all([
      unwrap<any[]>(api.get("/admin/categories")),
      unwrap<any[]>(api.get("/admin/tags")),
    ]);
    rows.value = categoryData;
    tagRows.value = tagData;
  } finally {
    loading.value = false;
  }
};

const categoryTypeText = (type: string) => {
  const map: Record<string, string> = {
    article: "新闻",
    case: "案例",
    download: "下载",
  };
  return map[type] || type;
};

const resetForm = () => {
  form.name = "";
  form.slug = "";
  form.type = "article";
  form.parent_id = null;
  form.sort_order = 0;
  form.enabled = true;
  slugTouched.value = false;
};

const resetTagForm = () => {
  tagForm.name = "";
  tagForm.slug = "";
  tagForm.type = "content";
  tagForm.color = "";
  tagForm.enabled = true;
  tagSlugTouched.value = false;
};

const openCreate = () => {
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
};

const openTagCreate = () => {
  tagEditingId.value = null;
  resetTagForm();
  tagDialogVisible.value = true;
};

const openEdit = (row: any) => {
  editingId.value = row.id;
  form.name = row.name;
  form.slug = row.slug;
  form.type = row.type;
  form.parent_id = row.parent_id;
  form.sort_order = row.sort_order;
  form.enabled = row.enabled;
  slugTouched.value = true;
  dialogVisible.value = true;
};

const openTagEdit = (row: any) => {
  tagEditingId.value = row.id;
  tagForm.name = row.name;
  tagForm.slug = row.slug;
  tagForm.type = row.type;
  tagForm.color = row.color || "";
  tagForm.enabled = row.enabled;
  tagSlugTouched.value = true;
  tagDialogVisible.value = true;
};

const submit = async () => {
  const payload = { ...form };
  if (editingId.value) {
    await unwrap(api.put(`/admin/categories/${editingId.value}`, payload));
  } else {
    await unwrap(api.post("/admin/categories", payload));
  }
  ElMessage.success("保存成功");
  dialogVisible.value = false;
  editingId.value = null;
  resetForm();
  await load();
};

const submitTag = async () => {
  const payload = { ...tagForm, color: tagForm.color || null };
  if (tagEditingId.value) {
    await unwrap(api.put(`/admin/tags/${tagEditingId.value}`, payload));
  } else {
    await unwrap(api.post("/admin/tags", payload));
  }
  ElMessage.success("保存成功");
  tagDialogVisible.value = false;
  tagEditingId.value = null;
  resetTagForm();
  await load();
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
      <div>
        <div style="font-size: 30px; font-weight: 700;">分类管理</div>
        <div style="margin-top: 8px; color: #64748b;">维护新闻、案例和下载等内容分类。</div>
      </div>
      <el-button type="primary" @click="openCreate">新增分类</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" style="margin-top: 24px;">
      <el-table-column prop="name" label="标题" min-width="180" />
      <el-table-column prop="slug" label="标识" min-width="180" />
      <el-table-column prop="type" label="类型" width="140">
        <template #default="{ row }">
          {{ categoryTypeText(row.type) }}
        </template>
      </el-table-column>
      <el-table-column label="启用" width="100">
        <template #default="{ row }">
          {{ row.enabled ? "是" : "否" }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑内容' : '新建内容'" width="640">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="标识">
          <el-input v-model="form.slug" @input="slugTouched = true" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%;">
            <el-option label="新闻" value="article" />
            <el-option label="案例" value="case" />
            <el-option label="下载" value="download" />
          </el-select>
        </el-form-item>
        <el-form-item label="上级分类">
          <el-select v-model="form.parent_id" clearable style="width: 100%;">
            <el-option
              v-for="item in rows.filter((item) => item.id !== editingId)"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 36px;">
      <div>
        <div style="font-size: 24px; font-weight: 700;">标签管理</div>
        <div style="margin-top: 8px; color: #64748b;">维护新闻和案例的基础标签。</div>
      </div>
      <el-button type="primary" plain @click="openTagCreate">新增标签</el-button>
    </div>

    <el-table :data="tagRows" v-loading="loading" style="margin-top: 18px;">
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="slug" label="标识" min-width="180" />
      <el-table-column prop="type" label="类型" width="140" />
      <el-table-column prop="color" label="颜色" width="120" />
      <el-table-column label="启用" width="100">
        <template #default="{ row }">
          {{ row.enabled ? "是" : "否" }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openTagEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="tagDialogVisible" :title="tagEditingId ? '编辑标签' : '新建标签'" width="640">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="tagForm.name" />
        </el-form-item>
        <el-form-item label="标识">
          <el-input v-model="tagForm.slug" @input="tagSlugTouched = true" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="tagForm.type" style="width: 100%;">
            <el-option label="新闻" value="新闻" />
            <el-option label="案例" value="案例" />
            <el-option label="内容" value="content" />
          </el-select>
        </el-form-item>
        <el-form-item label="颜色">
          <el-input v-model="tagForm.color" placeholder="#2563eb" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="tagForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTag">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>
