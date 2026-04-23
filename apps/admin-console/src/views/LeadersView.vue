<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, reactive, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const rows = ref<any[]>([]);
const loading = ref(false);
const dialogVisible = ref(false);
const editingId = ref<number | null>(null);
const uploading = ref(false);
const selectedFile = ref<File | null>(null);

const form = reactive({
  name: "",
  title: "",
  photo_file_id: null as number | null,
  intro: "",
  sort_order: 0,
  is_visible: true,
});

const load = async () => {
  loading.value = true;
  try {
    rows.value = await unwrap<any[]>(api.get("/admin/leaders"));
  } finally {
    loading.value = false;
  }
};

const resetForm = () => {
  form.name = "";
  form.title = "";
  form.photo_file_id = null;
  form.intro = "";
  form.sort_order = 0;
  form.is_visible = true;
  selectedFile.value = null;
};

const openCreate = () => {
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
};

const openEdit = (row: any) => {
  editingId.value = row.id;
  form.name = row.name;
  form.title = row.title;
  form.photo_file_id = row.photo_file_id;
  form.intro = row.intro || "";
  form.sort_order = row.sort_order || 0;
  form.is_visible = row.is_visible;
  selectedFile.value = null;
  dialogVisible.value = true;
};

const onFileChange = (file: any) => {
  selectedFile.value = file.raw;
};

const uploadPhoto = async () => {
  if (!selectedFile.value) return;
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append("upload", selectedFile.value);
    const file = await unwrap<any>(api.post("/admin/files/upload", formData));
    form.photo_file_id = file.id;
    ElMessage.success("上传成功");
  } finally {
    uploading.value = false;
  }
};

const submit = async () => {
  const payload = { ...form };
  if (editingId.value) {
    await unwrap(api.put(`/admin/leaders/${editingId.value}`, payload));
  } else {
    await unwrap(api.post("/admin/leaders", payload));
  }
  ElMessage.success("保存成功");
  dialogVisible.value = false;
  editingId.value = null;
  resetForm();
  await load();
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
      <div>
        <div style="font-size: 30px; font-weight: 700;">领导团队</div>
        <div style="margin-top: 8px; color: #64748b;">维护领导姓名、职务、简介和展示顺序。</div>
      </div>
      <el-button type="primary" @click="openCreate">新增内容</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" style="margin-top: 24px;">
      <el-table-column prop="name" label="姓名" min-width="160" />
      <el-table-column prop="title" label="职务" min-width="180" />
      <el-table-column prop="sort_order" label="排序" width="100" />
      <el-table-column label="显示" width="100">
        <template #default="{ row }">
          {{ row.is_visible ? "是" : "否" }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑内容' : '新建内容'" width="720">
      <el-form label-position="top">
        <el-form-item label="Name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="Title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item label="Photo">
          <div style="display: flex; gap: 12px;">
            <el-upload :auto-upload="false" :show-file-list="false" :on-change="onFileChange">
              <el-button>选择文件</el-button>
            </el-upload>
            <el-button :loading="uploading" @click="uploadPhoto">上传</el-button>
            <span style="color: #64748b;">{{ form.photo_file_id ? `文件 ID: ${form.photo_file_id}` : "未上传" }}</span>
          </div>
        </el-form-item>
        <el-form-item label="Intro">
          <el-input v-model="form.intro" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="Sort Order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="Visible">
          <el-switch v-model="form.is_visible" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>
