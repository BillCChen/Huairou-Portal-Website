<script setup lang="ts">
import { ElMessage } from "element-plus";
import { onMounted, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const files = ref<any[]>([]);
const downloads = ref<any[]>([]);
const selectedFile = ref<File | null>(null);

const scanStatusLabel = (status?: string) => {
  const labels: Record<string, string> = {
    pending: "待扫描",
    clean: "已通过",
    infected: "风险文件",
    failed: "扫描失败",
    skipped: "已跳过",
  };
  return labels[status || "pending"] || "待扫描";
};

const scanStatusType = (status?: string) => {
  const types: Record<string, "success" | "warning" | "danger" | "info"> = {
    pending: "warning",
    clean: "success",
    infected: "danger",
    failed: "danger",
    skipped: "info",
  };
  return types[status || "pending"] || "warning";
};

const load = async () => {
  const [fileData, downloadData] = await Promise.all([
    unwrap<any[]>(api.get("/admin/files")),
    unwrap<{ items: any[] }>(api.get("/admin/downloads", { params: { page: 1, page_size: 100 } })),
  ]);
  files.value = fileData;
  downloads.value = downloadData.items || [];
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

const mockScanFile = async (row: any) => {
  await unwrap(api.post(`/admin/files/${row.id}/mock-scan`));
  ElMessage.success("模拟扫描完成");
  await load();
};

const downloadResource = async (row: any) => {
  try {
    const response = await api.get(`/downloads/${row.id}/download`, { responseType: "blob" });
    const contentType = String(response.headers["content-type"] || "application/octet-stream");
    const blob = new Blob([response.data], { type: contentType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = row.file?.origin_name || row.title || "download";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch {
    ElMessage.error("下载失败，请确认权限或文件状态");
  }
};

onMounted(load);
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
      <div>
        <div style="font-size: 30px; font-weight: 700;">文件库</div>
        <div style="margin-top: 8px; color: #64748b;">文件通过后端接口下载，存储路径不在页面展示。</div>
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
      <el-table-column prop="mime_type" label="文件类型" min-width="180" />
      <el-table-column prop="size" label="大小" width="120" />
      <el-table-column label="扫描状态" width="120">
        <template #default="{ row }">
          <el-tag :type="scanStatusType(row.scan_status)">
            {{ scanStatusLabel(row.scan_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="scanned_at" label="扫描时间" min-width="180" />
      <el-table-column prop="scan_message" label="扫描说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作" width="130">
        <template #default="{ row }">
          <el-button size="small" @click="mockScanFile(row)">模拟扫描</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div style="margin-top: 32px;">
      <div style="font-size: 22px; font-weight: 700;">下载资源</div>
      <div style="margin-top: 8px; color: #64748b;">公开资源允许匿名下载，受保护资源仅 active 登录用户可下载。</div>
    </div>
    <el-table :data="downloads" style="margin-top: 16px;">
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column prop="file.origin_name" label="关联文件" min-width="220" />
      <el-table-column label="扫描状态" width="120">
        <template #default="{ row }">
          <el-tag :type="scanStatusType(row.file?.scan_status)">
            {{ scanStatusLabel(row.file?.scan_status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="访问范围" width="120">
        <template #default="{ row }">
          <el-tag :type="row.is_public ? 'success' : 'warning'">
            {{ row.is_public ? "公开" : "受保护" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="download_count" label="下载次数" width="120" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="downloadResource(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>
  </AppLayout>
</template>
