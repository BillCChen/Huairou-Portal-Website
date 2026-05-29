<script setup lang="ts">
const route = useRoute();
const currentUser = ref<any>(null);
const authReady = ref(false);

type NavItem = {
  label: string;
  to?: string;
  href?: string;
};

const items: Array<{ label: string; to: string }> = [
  { label: "首页", to: "/" },
  { label: "新闻动态", to: "/news" },
  { label: "成功案例", to: "/cases" },
  { label: "关于我们", to: "/about" },
  { label: "研究所展示", to: "/institutes" },
  { label: "在线服务", to: "/service" },
];

const resourcePlatformBaseUrl = "https://cg.huairou.tech";

const groupedNavItems: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "成果与平台",
    items: [
      { label: "找成果", href: `${resourcePlatformBaseUrl}/achievements` },
      { label: "找人才", href: `${resourcePlatformBaseUrl}/talents` },
      { label: "找设施", href: `${resourcePlatformBaseUrl}/facilities` },
    ],
  },
  {
    label: "业务与系统",
    items: [
      { label: "搜索与数据统计", to: "/search-stats" },
      { label: "客户端适配", to: "/adaptation" },
      { label: "业务系统模块", to: "/systems" },
    ],
  },
];

const openGroups = reactive<Record<string, boolean>>({});
const hoverOpenTimers = new Map<string, ReturnType<typeof setTimeout>>();
const hoverCloseTimers = new Map<string, ReturnType<typeof setTimeout>>();

const roleLabels: Record<string, string> = {
  super_admin: "超级管理员",
  content_admin: "内容管理员",
  auditor: "审核员",
  institute_editor: "机构用户",
  registered_user: "注册用户",
};

const displayName = computed(() => currentUser.value?.real_name || currentUser.value?.username || "用户");
const displayRole = computed(() => {
  const roleName = currentUser.value?.role_name;
  if (roleName) {
    return roleName;
  }
  const roleCode = currentUser.value?.role_code;
  return roleCode ? roleLabels[roleCode] || roleCode : "用户";
});

const clearOpenTimer = (label: string) => {
  const timer = hoverOpenTimers.get(label);
  if (!timer) {
    return;
  }
  clearTimeout(timer);
  hoverOpenTimers.delete(label);
};

const clearCloseTimer = (label: string) => {
  const timer = hoverCloseTimers.get(label);
  if (!timer) {
    return;
  }
  clearTimeout(timer);
  hoverCloseTimers.delete(label);
};

const openGroup = (label: string) => {
  clearCloseTimer(label);
  openGroups[label] = true;
};

const closeGroup = (label: string) => {
  clearOpenTimer(label);
  openGroups[label] = false;
};

const toggleGroup = (label: string) => {
  clearOpenTimer(label);
  clearCloseTimer(label);
  openGroups[label] = !openGroups[label];
};

const scheduleHoverOpen = (label: string) => {
  clearCloseTimer(label);
  clearOpenTimer(label);
  hoverOpenTimers.set(label, setTimeout(() => openGroup(label), 1000));
};

const scheduleHoverClose = (label: string) => {
  clearOpenTimer(label);
  clearCloseTimer(label);
  hoverCloseTimers.set(label, setTimeout(() => closeGroup(label), 3000));
};

const isActive = (to?: string) => {
  if (!to) {
    return false;
  }
  return to === "/" ? route.path === "/" : route.path.startsWith(to);
};

const loadCurrentUser = async () => {
  if (!import.meta.client) {
    return;
  }
  try {
    currentUser.value = await getCurrentPortalUser();
  } catch {
    clearPortalSession();
    currentUser.value = null;
  } finally {
    authReady.value = true;
  }
};

const logout = async () => {
  clearPortalSession();
  currentUser.value = null;
  await navigateTo("/");
};

onMounted(() => {
  loadCurrentUser();
  window.addEventListener("portal-auth-changed", loadCurrentUser);
});

onBeforeUnmount(() => {
  hoverOpenTimers.forEach((timer) => clearTimeout(timer));
  hoverCloseTimers.forEach((timer) => clearTimeout(timer));
  hoverOpenTimers.clear();
  hoverCloseTimers.clear();
  if (import.meta.client) {
    window.removeEventListener("portal-auth-changed", loadCurrentUser);
  }
});
</script>

<template>
  <header class="site-header">
    <div class="container site-header__inner">
      <NuxtLink to="/" class="site-header__logo">
        <div class="site-header__logo-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="12" stroke="rgba(255,255,255,0.4)" stroke-width="1.5"/>
            <circle cx="14" cy="14" r="6" fill="rgba(255,255,255,0.9)"/>
          </svg>
        </div>
        <div class="site-header__logo-text">
          <span class="site-header__logo-en">LIFE SCIENCE INSTITUTE</span>
          <span class="site-header__logo-cn">生命科学产业创新研究院</span>
        </div>
      </NuxtLink>

      <nav class="site-header__nav">
        <NuxtLink
          v-for="item in items"
          :key="item.to"
          :to="item.to"
          class="site-header__nav-item"
          :class="{ 'is-active': isActive(item.to) }"
        >
          {{ item.label }}
        </NuxtLink>
        <div
          v-for="group in groupedNavItems"
          :key="group.label"
          class="site-header__group"
          @mouseenter="scheduleHoverOpen(group.label)"
          @mouseleave="scheduleHoverClose(group.label)"
        >
          <div
            class="site-header__dropdown"
            :class="{ 'is-open': openGroups[group.label] }"
          >
            <button
              type="button"
              class="site-header__group-label"
              :class="{ 'is-active': group.items.some((item) => isActive(item.to)) }"
              :aria-expanded="openGroups[group.label] ? 'true' : 'false'"
              @click="toggleGroup(group.label)"
            >
              {{ group.label }}
            </button>
            <div class="site-header__submenu" @keydown.esc="closeGroup(group.label)">
              <template v-for="child in group.items" :key="child.to || child.href">
                <NuxtLink
                  v-if="child.to"
                  :to="child.to"
                  class="site-header__submenu-item"
                  :class="{ 'is-active': isActive(child.to) }"
                >
                  {{ child.label }}
                </NuxtLink>
                <a
                  v-else
                  :href="child.href"
                  class="site-header__submenu-item"
                >
                  {{ child.label }}
                </a>
              </template>
            </div>
          </div>
        </div>
        <div v-if="authReady && currentUser" class="site-header__account">
          <span class="site-header__account-name">{{ displayName }}</span>
          <span class="site-header__role">{{ displayRole }}</span>
          <NuxtLink to="/profile" class="site-header__account-link">个人中心</NuxtLink>
          <button type="button" class="site-header__logout" @click="logout">退出</button>
        </div>
        <div v-else class="site-header__auth-links">
          <NuxtLink to="/login" class="site-header__login">登录</NuxtLink>
          <NuxtLink to="/register" class="site-header__register">注册</NuxtLink>
        </div>
      </nav>
    </div>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--primary-dark);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.site-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
}

.site-header__logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  flex-shrink: 0;
}

.site-header__logo-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.site-header__logo-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.site-header__logo-en {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.5);
  letter-spacing: 0.1em;
  line-height: 1;
}

.site-header__logo-cn {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  letter-spacing: 0.02em;
}

.site-header__nav {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.site-header__nav-item {
  padding: 6px 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.82);
  text-decoration: none;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  line-height: 36px;
}

.site-header__nav-item:hover {
  color: #fff;
}

.site-header__nav-item.is-active {
  color: #fff;
  border-bottom-color: #fff;
  font-weight: 600;
}

.site-header__auth-links,
.site-header__account {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-left: 8px;
}

.site-header__login,
.site-header__register,
.site-header__account-link,
.site-header__logout {
  margin-left: 8px;
  padding: 7px 18px;
  font-size: 13px;
  color: var(--primary-dark);
  background: #fff;
  border-radius: 2px;
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s;
}

.site-header__register {
  margin-left: 0;
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
}

.site-header__account-link,
.site-header__logout {
  margin-left: 0;
  padding: 6px 10px;
}

.site-header__logout {
  border: 0;
  cursor: pointer;
  font-family: inherit;
}

.site-header__login:hover,
.site-header__account-link:hover,
.site-header__logout:hover {
  background: #e8eef8;
}

.site-header__register:hover {
  background: rgba(255, 255, 255, 0.24);
}

.site-header__account-name {
  max-width: 96px;
  overflow: hidden;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-header__role {
  padding: 4px 8px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  white-space: nowrap;
}

.site-header__group {
  position: relative;
}

.site-header__dropdown {
  display: inline-flex;
  position: relative;
}

.site-header__dropdown.is-open .site-header__group-label::after {
  transform: rotate(180deg);
}

.site-header__group-label {
  border: 0;
  padding: 6px 12px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.82);
  text-decoration: none;
  white-space: nowrap;
  border-bottom: 2px solid transparent;
  background: transparent;
  transition: color 0.15s, border-color 0.15s;
  line-height: 36px;
  cursor: pointer;
  user-select: none;
  font-family: inherit;
}

.site-header__group-label::after {
  content: "▾";
  font-size: 10px;
  margin-left: 6px;
  display: inline-block;
  transition: transform 1.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.site-header__group-label:hover {
  color: #fff;
}

.site-header__group-label.is-active {
  color: #fff;
  border-bottom-color: #fff;
  font-weight: 600;
}

.site-header__dropdown.is-open .site-header__submenu {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
  transition-duration: 1.5s, 1.5s, 1.5s;
}

.site-header__submenu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 170px;
  padding: 10px;
  border-radius: 4px;
  background: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 10px 26px rgba(7, 26, 73, 0.2);
  display: flex;
  flex-direction: column;
  gap: 2px;
  opacity: 0;
  transform: translateY(12px) scale(0.96);
  transform-origin: top right;
  transition-property: opacity, transform, filter;
  transition-duration: 3s, 3s, 3s;
  transition-timing-function: cubic-bezier(0.22, 1, 0.36, 1);
  filter: blur(2px);
  pointer-events: none;
  z-index: 140;
}

.site-header__dropdown.is-open .site-header__submenu {
  filter: blur(0);
}

.site-header__submenu-item {
  display: block;
  padding: 9px 10px;
  color: #0f2f61;
  border-radius: 3px;
  text-decoration: none;
}

.site-header__submenu-item:hover {
  background: #f3f7fe;
  color: #0a2e86;
}

.site-header__submenu-item.is-active {
  background: rgba(10, 78, 168, 0.09);
  color: #0a2e86;
  font-weight: 600;
}
</style>
