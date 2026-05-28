<script setup lang="ts">
import { Document, Files, House, PictureFilled, Setting, User } from "@element-plus/icons-vue";
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "../stores/auth";

const route = useRoute();
const auth = useAuthStore();

type MenuLeaf = { path: string; label: string; icon: any };
type MenuGroup = { label: string; icon: any; children: MenuLeaf[] };
type MenuItem = MenuLeaf | MenuGroup;

const menus = computed<MenuItem[]>(() => [
  { path: "/dashboard", label: "仪表盘", icon: House },
  { path: "/articles", label: "新闻管理", icon: Document },
  { path: "/cases", label: "成功案例", icon: PictureFilled },
  { path: "/pages", label: "单页内容", icon: Document },
  { path: "/institutes", label: "研究所展示", icon: Document },
  {
    label: "业务与系统",
    icon: Document,
    children: [
      { path: "/pages/search-stats", label: "搜索与数据统计", icon: Document },
      { path: "/pages/adaptation", label: "客户端适配", icon: Files },
      { path: "/pages/systems", label: "业务系统模块", icon: Document },
    ],
  },
  { path: "/banners", label: "轮播图管理", icon: PictureFilled },
  { path: "/categories", label: "分类标签", icon: Document },
  { path: "/leaders", label: "领导团队", icon: User },
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
          <div style="font-size: 13px; color: #64748b; letter-spacing: 0.12em;">门户网站管理后台</div>
          <div style="font-size: 22px; font-weight: 700; margin-top: 6px;">内容管理后台</div>
        </div>
        <el-menu
          :default-active="route.path"
          router
          style="border-right: none; background: transparent;"
        >
          <template v-for="menu in menus" :key="menu.label">
            <el-sub-menu v-if="'children' in menu" :index="menu.label">
              <template #title>
                <el-icon><component :is="menu.icon" /></el-icon>
                <span>{{ menu.label }}</span>
              </template>
              <el-menu-item v-for="child in menu.children" :key="child.path" :index="child.path">
                <el-icon><component :is="child.icon" /></el-icon>
                <span>{{ child.label }}</span>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="menu.path">
              <el-icon><component :is="menu.icon" /></el-icon>
              <span>{{ menu.label }}</span>
            </el-menu-item>
          </template>
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
