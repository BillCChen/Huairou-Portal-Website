<script setup lang="ts">
import { CollectionTag, Document, Files, House, PictureFilled, Setting, User } from "@element-plus/icons-vue";
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "../stores/auth";

const route = useRoute();
const auth = useAuthStore();

const menus = computed(() => [
  { path: "/dashboard", label: "仪表盘", icon: House },
  { path: "/articles", label: "新闻管理", icon: Document },
  { path: "/cases", label: "成功案例", icon: PictureFilled },
  { path: "/pages", label: "单页内容", icon: Document },
  { path: "/banners", label: "Banner 管理", icon: PictureFilled },
  { path: "/categories", label: "分类管理", icon: CollectionTag },
  { path: "/leaders", label: "领导团队", icon: User },
  { path: "/institutes", label: "研究所管理", icon: Document },
  { path: "/files", label: "文件库", icon: Files },
  { path: "/users", label: "用户审核", icon: User },
  { path: "/audit-logs", label: "审计日志", icon: Document },
  { path: "/settings", label: "站点设置", icon: Setting },
]);
</script>

<template>
  <el-container class="app-shell">
    <el-aside width="260px" style="padding: 20px;">
      <div class="content-card" style="padding: 24px; min-height: calc(100vh - 40px);">
        <div style="margin-bottom: 28px;">
          <div style="font-size: 13px; color: #64748b; letter-spacing: 0.12em;">PORTAL CMS</div>
          <div style="font-size: 22px; font-weight: 700; margin-top: 6px;">内容管理后台</div>
        </div>
        <el-menu
          :default-active="route.path"
          router
          style="border-right: none; background: transparent;"
        >
          <el-menu-item v-for="menu in menus" :key="menu.path" :index="menu.path">
            <el-icon><component :is="menu.icon" /></el-icon>
            <span>{{ menu.label }}</span>
          </el-menu-item>
        </el-menu>
        <div style="margin-top: auto; padding-top: 24px; border-top: 1px solid #e2e8f0;">
          <div style="font-size: 14px; font-weight: 600;">{{ auth.user?.real_name }}</div>
          <div style="font-size: 12px; color: #64748b; margin-top: 4px;">管理员会话</div>
          <el-button style="margin-top: 16px;" plain @click="auth.logout()">退出登录</el-button>
        </div>
      </div>
    </el-aside>
    <el-main style="padding: 20px 20px 20px 0;">
      <div class="content-card" style="padding: 28px; min-height: calc(100vh - 40px);">
        <slot />
      </div>
    </el-main>
  </el-container>
</template>
