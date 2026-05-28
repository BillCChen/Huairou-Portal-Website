<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, unwrap } from "../api/client";
import AppLayout from "../components/AppLayout.vue";

const stats = ref({
  articles: 0,
  cases: 0,
  pages: 0,
  pending_users: 0,
  service_requests: 0,
});

const statsLabel = {
  articles: "新闻",
  cases: "成功案例",
  pages: "单页",
  pending_users: "待审核用户",
  service_requests: "服务申请",
};

onMounted(async () => {
  stats.value = await unwrap(api.get("/admin/dashboard"));
});
</script>

<template>
  <AppLayout>
    <div style="display: flex; justify-content: space-between; gap: 16px; align-items: end;">
      <div>
        <div style="font-size: 32px; font-weight: 700;">站点概览</div>
      <div style="margin-top: 8px; color: #64748b;">当前后台覆盖新闻、案例、单页、轮播图、注册审核和站点配置。</div>
      </div>
    </div>
    <el-row :gutter="18" style="margin-top: 24px;">
      <el-col :span="6" v-for="(value, key) in stats" :key="key">
        <div class="content-card" style="padding: 22px; background: #f8fbff;">
          <div style="font-size: 13px; color: #64748b;">{{ statsLabel[key as keyof typeof statsLabel] }}</div>
          <div style="font-size: 34px; font-weight: 700; margin-top: 12px;">{{ value }}</div>
        </div>
      </el-col>
    </el-row>
    <el-alert
      type="info"
      show-icon
      style="margin-top: 28px;"
      title="研究所、人才服务、在线服务和产学研合作仍按可配置/预留方式设计，未将待确认业务规则写死。"
    />
  </AppLayout>
</template>
