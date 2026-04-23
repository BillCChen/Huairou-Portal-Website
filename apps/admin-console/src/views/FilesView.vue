<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const files = ref<any[]>([]);
const selectedFile = ref<File | null>(null);

const load = async () => {
  files.value = await unwrap<any[]>(api.get("/admin/files"));
};

const onFileChange = (file: any) => {
  selectedFile.value = file.raw;
};

const upload = async () => {
  if (!selectedFile.value) return;
  const formData = new FormData();
  formData.append("upload", selectedFile.value);
  await unwrap(api.post("/admin/files/upload", formData));
  ElMessage.success("上传成功");
  selectedFile.value = null;
  await load();
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
      <div>
        <div style="font-size: 30px; font-weight: 700;">文件库</div>
        <div style="margin-top: 8px; color: #64748b;">支持图片与附件上传，后续可接入富文本引用和下载资源。</div>
      </div>
      <div style="display: flex; gap: 12px;">
        <el-upload :auto-upload="false" :show-file-list="false" :on-change="onFileChange">
          <el-button>选择文件</el-button>
        </el-upload>
        <el-button type="primary" @click="upload">上传</el-button>
      </div>
    </div>
    <el-table :data="files" style="margin-top: 24px;">
      <el-table-column prop="origin_name" label="文件名" min-width="240" />
      <el-table-column prop="mime_type" label="MIME" min-width="180" />
      <el-table-column prop="size" label="大小" width="120" />
      <el-table-column prop="storage_path" label="存储路径" min-width="220" />
    </el-table>
  </AppLayout>
</template>
