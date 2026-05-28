import { createRouter, createWebHistory } from "vue-router";

import { useAuthStore } from "../stores/auth";
import DashboardView from "../views/DashboardView.vue";
import FilesView from "../views/FilesView.vue";
import ListView from "../views/ListView.vue";
import LoginView from "../views/LoginView.vue";
import AuditLogsView from "../views/AuditLogsView.vue";
import CategoriesView from "../views/CategoriesView.vue";
import InstitutesView from "../views/InstitutesView.vue";
import LeadersView from "../views/LeadersView.vue";
import SettingsView from "../views/SettingsView.vue";
import UsersView from "../views/UsersView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { public: true } },
    { path: "/", redirect: "/dashboard" },
    { path: "/dashboard", component: DashboardView },
    { path: "/articles", component: ListView, props: { kind: "articles", title: "新闻管理" } },
    { path: "/cases", component: ListView, props: { kind: "cases", title: "成功案例" } },
    { path: "/pages", component: ListView, props: { kind: "pages", title: "单页内容" } },
    { path: "/pages/cooperation", component: ListView, props: { kind: "pages", pageKey: "cooperation", title: "产学研合作" } },
    { path: "/pages/incubation", component: ListView, props: { kind: "pages", pageKey: "incubation", title: "成果孵化" } },
    { path: "/pages/platforms", component: ListView, props: { kind: "pages", pageKey: "platforms", title: "共性平台" } },
    { path: "/pages/search-stats", component: ListView, props: { kind: "pages", pageKey: "search-stats", title: "搜索与数据统计" } },
    { path: "/pages/adaptation", component: ListView, props: { kind: "pages", pageKey: "adaptation", title: "客户端适配" } },
    { path: "/pages/systems", component: ListView, props: { kind: "pages", pageKey: "systems", title: "业务系统模块" } },
    { path: "/banners", component: ListView, props: { kind: "banners", title: "首页轮播图" } },
    { path: "/categories", component: CategoriesView },
    { path: "/leaders", component: LeadersView },
    { path: "/institutes", component: InstitutesView },
    { path: "/audit-logs", component: AuditLogsView },
    { path: "/files", component: FilesView },
    { path: "/users", component: UsersView },
    { path: "/settings", component: SettingsView },
  ],
});

router.beforeEach(async (to) => {
  const store = useAuthStore();
  if (!store.user && store.token) {
    await store.restore();
  }
  if (!to.meta.public && !store.token) {
    return "/login";
  }
  if (to.path === "/login" && store.token) {
    return "/dashboard";
  }
  return true;
});

export default router;
