<script setup lang="ts">
import { ElMessage } from "element-plus";
import { computed, reactive, ref, watch } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const props = defineProps<{
  kind: "articles" | "cases" | "pages" | "banners";
  title: string;
  pageKey?: string;
}>();

const rows = ref<any[]>([]);
const categories = ref<any[]>([]);
const tags = ref<any[]>([]);
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
      content_html: "",
      category_id: null,
      cover_file_id: null,
      status: "draft",
      source: "",
      author: "",
      publish_at: null,
      is_top: false,
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
      content_html: "",
      category_id: null,
      cover_file_id: null,
      status: "draft",
      partner_name: "",
      stage: "",
      publish_at: null,
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
      content_html: "",
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
      tag: "院内新闻",
      sort_order: 0,
      is_enabled: true,
    },
  },
})[props.kind]);

const categoryType = computed(() => {
  if (props.kind === "articles") {
    return "article";
  }
  if (props.kind === "cases") {
    return "case";
  }
  return "";
});

const filteredCategories = computed(() =>
  categories.value.filter((item) => item.type === categoryType.value)
);

const filteredTags = computed(() => {
  if (props.kind === "articles") {
    return tags.value.filter((item) => ["新闻", "content", "article"].includes(item.type));
  }
  if (props.kind === "cases") {
    return tags.value.filter((item) => ["案例", "content", "case"].includes(item.type));
  }
  return tags.value;
});

const bannerTagOptions = [
  { label: "院内新闻", value: "院内新闻" },
  { label: "行业资讯", value: "行业资讯" },
  { label: "通知公告", value: "通知公告" },
  { label: "媒体聚焦", value: "媒体聚焦" },
];

const resetForm = () => {
  Object.assign(form, JSON.parse(JSON.stringify(routeConfig.value.initial)));
};

const normalizePayload = () => {
  const payload = JSON.parse(JSON.stringify(form));
  for (const key of ["category_id", "cover_file_id", "image_file_id"]) {
    if (payload[key] === "" || payload[key] === undefined) {
      payload[key] = null;
    }
  }
  if (payload.publish_at === "") {
    payload.publish_at = null;
  }
  return payload;
};

const updateJsonField = (field: string, value: string, fallback: any) => {
  try {
    form[field] = JSON.parse(value || "null") ?? fallback;
  } catch {
    ElMessage.error("JSON 格式无效");
  }
};

const openCreate = () => {
  editingId.value = null;
  resetForm();
  if (props.kind === "pages" && props.pageKey) {
    form.page_key = props.pageKey;
  }
  dialogVisible.value = true;
};

const openEdit = (row: any) => {
  editingId.value = row.id;
  resetForm();
  Object.assign(form, JSON.parse(JSON.stringify(row)));
  if (props.kind === "pages" && props.pageKey) {
    form.page_key = props.pageKey;
  }
  if (props.kind === "banners" && !form.tag) {
    form.tag = "院内新闻";
  }
  dialogVisible.value = true;
};

const load = async () => {
  loading.value = true;
  try {
    const listEndpoint =
      props.kind === "pages" && props.pageKey
        ? `${routeConfig.value.list}?page_key=${encodeURIComponent(props.pageKey)}`
        : routeConfig.value.list;
    const data = await unwrap<any>(api.get(listEndpoint));
    rows.value = Array.isArray(data) ? data : data.items || [];
    if (props.kind === "articles" || props.kind === "cases") {
      const [categoryData, tagData] = await Promise.all([
        unwrap<any[]>(api.get("/admin/categories")),
        unwrap<any[]>(api.get("/admin/tags")),
      ]);
      categories.value = categoryData;
      tags.value = tagData;
    }
    editingId.value = null;
    dialogVisible.value = false;
    resetForm();
  } finally {
    loading.value = false;
  }
};

const formatDate = (value?: string | null) => {
  if (!value) {
    return "-";
  }
  return new Date(value).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatStatus = (status: string) => {
  const labels: Record<string, string> = {
    draft: "草稿",
    published: "已发布",
    offline: "下线",
    hidden: "隐藏",
    active: "启用中",
    pending: "待审核",
    disabled: "禁用",
  };
  return labels[status] || status;
};

const submit = async () => {
  if (props.kind === "pages" && props.pageKey) {
    form.page_key = props.pageKey;
  }
  const payload = normalizePayload();
  try {
    if (editingId.value) {
      await unwrap(api.put(`${routeConfig.value.submit}/${editingId.value}`, payload));
    } else {
      await unwrap(api.post(routeConfig.value.submit, payload));
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

watch(
  () => [props.kind, props.pageKey],
  async () => {
    resetForm();
    await load();
  },
  { immediate: true }
);
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
      <el-table-column v-if="props.kind === 'pages'" prop="page_key" label="页面标识" min-width="180">
        <template #default="{ row }">
          {{ row.page_key || row.slug || row.id }}
        </template>
      </el-table-column>
      <el-table-column v-if="props.kind !== 'pages'" prop="slug" label="标识" min-width="160">
        <template #default="{ row }">
          {{ row.slug || row.page_key || row.id }}
        </template>
      </el-table-column>
      <el-table-column
        v-if="props.kind === 'articles'"
        prop="source"
        label="来源"
        min-width="140"
      />
      <el-table-column
        v-if="props.kind === 'articles'"
        prop="author"
        label="作者"
        min-width="120"
      />
      <el-table-column
        v-if="props.kind === 'cases'"
        prop="partner_name"
        label="合作方"
        min-width="140"
      />
      <el-table-column
        v-if="props.kind === 'cases'"
        prop="stage"
        label="阶段"
        min-width="120"
      />
      <el-table-column
        v-if="props.kind === 'banners'"
        prop="subtitle"
        label="副标题"
        min-width="220"
      />
      <el-table-column
        v-if="props.kind === 'banners'"
        prop="button_text"
        label="按钮文案"
        min-width="140"
      />
      <el-table-column
        v-if="props.kind === 'banners'"
        label="启用"
        width="90"
      >
        <template #default="{ row }">
          {{ row.is_enabled ? "是" : "否" }}
        </template>
      </el-table-column>
      <el-table-column
        v-if="props.kind === 'banners'"
        prop="sort_order"
        label="排序"
        width="90"
      />
      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          {{ formatStatus(row.status) }}
        </template>
      </el-table-column>
      <el-table-column prop="publish_at" label="发布时间" min-width="180">
        <template #default="{ row }">
          {{ formatDate(row.publish_at || row.updated_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑内容' : '新建内容'" width="760">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="form.title" />
        </el-form-item>
        <el-form-item v-if="props.kind !== 'banners' && props.kind !== 'pages'" label="标识">
          <el-input v-model="form.slug" />
        </el-form-item>
        <el-form-item v-if="props.kind === 'articles' || props.kind === 'cases'" label="分类">
          <el-select v-model="form.category_id" clearable style="width: 100%;">
            <el-option
              v-for="item in filteredCategories"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="props.kind === 'articles' || props.kind === 'cases'" label="标签">
          <el-select v-model="form.tag_ids" multiple clearable style="width: 100%;">
            <el-option
              v-for="item in filteredTags"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="props.kind === 'pages'" label="页面键">
          <el-input v-model="form.page_key" :disabled="Boolean(props.pageKey)" />
        </el-form-item>
        <el-form-item v-if="props.kind !== 'banners'" label="摘要">
          <el-input v-model="form.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item v-if="props.kind !== 'banners'" label="内容">
          <el-input v-model="form.content_html" type="textarea" :rows="8" />
        </el-form-item>
        <template v-if="props.kind === 'articles'">
          <el-form-item label="来源">
            <el-input v-model="form.source" />
          </el-form-item>
          <el-form-item label="作者">
            <el-input v-model="form.author" />
          </el-form-item>
          <el-form-item label="封面文件编号">
            <el-input-number v-model="form.cover_file_id" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="置顶">
            <el-switch v-model="form.is_top" />
          </el-form-item>
          <el-form-item label="发布时间">
            <el-input v-model="form.publish_at" placeholder="2026-01-01T00:00:00Z" />
          </el-form-item>
        </template>
        <template v-if="props.kind === 'cases'">
          <el-form-item label="合作方">
            <el-input v-model="form.partner_name" />
          </el-form-item>
          <el-form-item label="阶段">
            <el-input v-model="form.stage" />
          </el-form-item>
          <el-form-item label="收益亮点">
            <el-input v-model="form.benefits" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="封面文件编号">
            <el-input-number v-model="form.cover_file_id" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="发布时间">
            <el-input v-model="form.publish_at" placeholder="2026-01-01T00:00:00Z" />
          </el-form-item>
          <el-form-item label="高亮标签 JSON">
            <el-input
              :model-value="JSON.stringify(form.highlights || [], null, 2)"
              type="textarea"
              :rows="4"
              @change="(value: string) => updateJsonField('highlights', value, [])"
            />
          </el-form-item>
          <el-form-item label="成果块 JSON">
            <el-input
              :model-value="JSON.stringify(form.result_blocks || [], null, 2)"
              type="textarea"
              :rows="5"
              @change="(value: string) => updateJsonField('result_blocks', value, [])"
            />
          </el-form-item>
        </template>
        <template v-if="props.kind === 'pages'">
          <el-form-item label="内容块 JSON">
            <el-input
              :model-value="JSON.stringify(form.blocks || [], null, 2)"
              type="textarea"
              :rows="5"
              @change="(value: string) => updateJsonField('blocks', value, [])"
            />
          </el-form-item>
        </template>
        <template v-if="props.kind === 'banners'">
          <el-form-item label="标签">
            <el-radio-group v-model="form.tag">
              <el-radio v-for="item in bannerTagOptions" :key="item.value" :label="item.value">
                {{ item.label }}
              </el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="副标题">
            <el-input v-model="form.subtitle" />
          </el-form-item>
          <el-form-item label="按钮文案">
            <el-input v-model="form.button_text" />
          </el-form-item>
          <el-form-item label="按钮链接">
            <el-input v-model="form.button_url" />
          </el-form-item>
          <el-form-item label="图片文件编号">
            <el-input-number v-model="form.image_file_id" :min="1" controls-position="right" />
          </el-form-item>
          <el-form-item label="排序">
            <el-input-number v-model="form.sort_order" :min="0" />
          </el-form-item>
          <el-form-item label="启用">
            <el-switch v-model="form.is_enabled" />
          </el-form-item>
        </template>
        <el-form-item v-if="props.kind !== 'banners'" label="状态">
          <el-select v-model="form.status" style="width: 180px;">
            <el-option label="草稿" value="draft" />
            <el-option label="已发布" value="published" />
            <el-option label="下线" value="offline" />
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
