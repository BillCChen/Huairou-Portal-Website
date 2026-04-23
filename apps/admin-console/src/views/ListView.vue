<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, onMounted, reactive, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const props = defineProps<{
  kind: "articles" | "cases" | "pages" | "banners";
  title: string;
}>();

const rows = ref<any[]>([]);
const dialogVisible = ref(false);
const loading = ref(false);
const editingId = ref<number | null>(null);
const form = reactive<any>({});

const routeConfig = computed(() => ({
  articles: {
    list: "/admin/articles",
    submit: "/admin/articles",
    initial: {
      title: "",
      slug: "",
      summary: "",
      content_html: "<p></p>",
      status: "draft",
      source: "",
      author: "",
      seo_title: "",
      seo_description: "",
      seo_keywords: "",
      tag_ids: [],
      attachments: [],
    },
  },
  cases: {
    list: "/admin/cases",
    submit: "/admin/cases",
    initial: {
      title: "",
      slug: "",
      summary: "",
      content_html: "<p></p>",
      status: "draft",
      partner_name: "",
      stage: "",
      benefits: "",
      highlights: [],
      result_blocks: [],
      tag_ids: [],
    },
  },
  pages: {
    list: "/admin/pages",
    submit: "/admin/pages",
    initial: {
      title: "",
      page_key: "",
      content_html: "<p></p>",
      status: "published",
      blocks: [],
    },
  },
  banners: {
    list: "/admin/banners",
    submit: "/admin/banners",
    initial: {
      title: "",
      subtitle: "",
      button_text: "",
      button_url: "",
      image_file_id: null,
      sort_order: 0,
      is_enabled: true,
    },
  },
})[props.kind]);

const resetForm = () => {
  Object.assign(form, JSON.parse(JSON.stringify(routeConfig.value.initial)));
};

const openCreate = () => {
  editingId.value = null;
  resetForm();
  dialogVisible.value = true;
};

const openEdit = (row: any) => {
  editingId.value = row.id;
  resetForm();
  Object.assign(form, JSON.parse(JSON.stringify(row)));
  dialogVisible.value = true;
};

const load = async () => {
  loading.value = true;
  try {
    const data = await unwrap<any>(api.get(routeConfig.value.list));
    rows.value = Array.isArray(data) ? data : data.items || [];
  } finally {
    loading.value = false;
  }
};

const submit = async () => {
  try {
    if (editingId.value) {
      await unwrap(api.put(`${routeConfig.value.submit}/${editingId.value}`, form));
    } else {
      await unwrap(api.post(routeConfig.value.submit, form));
    }
    ElMessage.success("保存成功");
    dialogVisible.value = false;
    editingId.value = null;
    resetForm();
    await load();
  } catch (error) {
    ElMessage.error("保存失败，请检查字段");
    console.error(error);
  }
};

onMounted(async () => {
  resetForm();
  await load();
});
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 16px;">
      <div>
        <div style="font-size: 30px; font-weight: 700;">{{ title }}</div>
        <div style="margin-top: 8px; color: #64748b;">当前提供基础录入与发布能力，复杂字段继续保留扩展位。</div>
      </div>
      <el-button type="primary" @click="openCreate">新增内容</el-button>
    </div>
    <el-table :data="rows" v-loading="loading" style="margin-top: 24px;">
      <el-table-column prop="title" label="标题" min-width="220" />
      <el-table-column prop="slug" label="Slug / Key" min-width="160">
        <template #default="{ row }">
          {{ row.slug || row.page_key || row.id }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="publish_at" label="发布时间" min-width="180" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑内容' : '新建内容'" width="760">
      <el-form label-position="top">
        <el-form-item label="Title">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item v-if="props.kind !== 'banners' && props.kind !== 'pages'" label="Slug">
          <el-input v-model="form.slug" />
        </el-form-item>
        <el-form-item v-if="props.kind === 'pages'" label="Page Key">
          <el-input v-model="form.page_key" />
        </el-form-item>
        <el-form-item v-if="props.kind !== 'banners'" label="Summary">
          <el-input v-model="form.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="props.kind !== 'banners'" label="Content HTML">
          <el-input v-model="form.content_html" type="textarea" :rows="8" />
        </el-form-item>
        <template v-if="props.kind === 'articles'">
          <el-form-item label="Source">
            <el-input v-model="form.source" />
          </el-form-item>
          <el-form-item label="Author">
            <el-input v-model="form.author" />
          </el-form-item>
        </template>
        <template v-if="props.kind === 'cases'">
          <el-form-item label="Partner Name">
            <el-input v-model="form.partner_name" />
          </el-form-item>
          <el-form-item label="Stage">
            <el-input v-model="form.stage" />
          </el-form-item>
          <el-form-item label="Benefits">
            <el-input v-model="form.benefits" type="textarea" :rows="3" />
          </el-form-item>
        </template>
        <template v-if="props.kind === 'banners'">
          <el-form-item label="Subtitle">
            <el-input v-model="form.subtitle" />
          </el-form-item>
          <el-form-item label="Button Text">
            <el-input v-model="form.button_text" />
          </el-form-item>
          <el-form-item label="Button URL">
            <el-input v-model="form.button_url" />
          </el-form-item>
        </template>
        <el-form-item v-if="props.kind !== 'banners'" label="Status">
          <el-select v-model="form.status" style="width: 180px;">
            <el-option label="Draft" value="draft" />
            <el-option label="Published" value="published" />
            <el-option label="Offline" value="offline" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false; editingId = null; resetForm();">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </AppLayout>
</template>
