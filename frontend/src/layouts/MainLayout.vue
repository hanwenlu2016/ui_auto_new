<template>
  <n-layout has-sider style="height: 100vh; background: var(--color-bg)">
    <!-- Sidebar -->
    <n-layout-sider
      collapse-mode="width"
      :collapsed-width="64"
      :width="220"
      :collapsed="collapsed"
      :native-scrollbar="false"
      class="sidebar"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <!-- Logo -->
      <div class="logo" :class="{ 'logo-collapsed': collapsed }">
        <div class="logo-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <rect width="24" height="24" rx="7" fill="url(#logoGrad)"/>
            <path d="M7 12l3 3 7-7" stroke="#fff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
                <stop stop-color="#4F81FF"/>
                <stop offset="1" stop-color="#7FA5FF"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span v-if="!collapsed" class="logo-text">UI Auto</span>
      </div>

      <!-- Navigation -->
      <div class="nav-section">
        <n-menu
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="20"
          :options="menuOptions"
          :value="activeKey"
          :indent="16"
          @update:value="handleMenuUpdate"
        />
      </div>

      <!-- Collapse trigger -->
      <div
        class="sidebar-trigger"
        :class="{ 'collapsed': collapsed }"
        @click="collapsed = !collapsed"
        title="折叠/展开"
      >
        <n-icon size="16" :class="{ 'rotate': collapsed }">
          <chevron-back-icon />
        </n-icon>
      </div>
    </n-layout-sider>

    <!-- Main area -->
    <n-layout style="background: var(--color-bg)">
      <!-- Header -->
      <div class="header">
        <div class="header-left">
          <n-breadcrumb class="breadcrumb">
            <n-breadcrumb-item>Home</n-breadcrumb-item>
            <n-breadcrumb-item>{{ currentRouteName }}</n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        <div class="header-right">
          <n-dropdown :options="userOptions" @select="handleUserSelect">
            <div class="user-btn">
              <div class="user-avatar">
                {{ (userStore.user?.full_name || 'U')[0].toUpperCase() }}
              </div>
              <span v-if="true" class="user-name">
                {{ userStore.user?.full_name || 'User' }}
              </span>
              <n-icon size="14" style="color: var(--color-text-3)">
                <chevron-down-icon />
              </n-icon>
            </div>
          </n-dropdown>
        </div>
      </div>

      <!-- Page Content -->
      <n-layout-content class="content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { h, ref, computed } from 'vue'
import type { Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NIcon,
  NLayout,
  NLayoutSider,
  NLayoutContent,
  NMenu,
  NBreadcrumb,
  NBreadcrumbItem,
  NDropdown,
} from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  HomeOutline as HomeIcon,
  FolderOutline as ProjectIcon,
  GridOutline as ModuleIcon,
  ListOutline as CaseIcon,
  VideocamOutline as RecordIcon,
  LogOutOutline as LogoutIcon,
  DocumentTextOutline as ReportIcon,
  ChevronBack as ChevronBackIcon,
  ChevronDown as ChevronDownIcon,
  LayersOutline as SuiteIcon,
  BrowsersOutline as PageIcon,
  CodeSlashOutline as ElementIcon,
} from '@vicons/ionicons5'
import { useUserStore } from '@/stores/user'

const collapsed = ref(false)
const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const activeKey = computed(() => route.name as string)
const currentRouteName = computed(() => route.name as string)

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const menuOptions: MenuOption[] = [
  {
    label: '仪表板',
    key: 'Dashboard',
    icon: renderIcon(HomeIcon)
  },
  {
    label: '项目管理',
    key: 'Projects',
    icon: renderIcon(ProjectIcon)
  },
  {
    label: '模块管理',
    key: 'Modules',
    icon: renderIcon(ModuleIcon)
  },
  {
    label: '页面管理',
    key: 'Pages',
    icon: renderIcon(PageIcon)
  },
  {
    label: '页面元素',
    key: 'PageElements',
    icon: renderIcon(ElementIcon)
  },
  {
    label: '测试用例',
    key: 'TestCases',
    icon: renderIcon(CaseIcon)
  },
  {
    label: '测试套件',
    key: 'TestSuites',
    icon: renderIcon(SuiteIcon)
  },
  {
    label: '录制',
    key: 'Recording',
    icon: renderIcon(RecordIcon)
  },
  {
    label: '报告管理',
    key: 'Reports',
    icon: renderIcon(ReportIcon)
  }
]

const userOptions = [
  {
    label: '退出登录',
    key: 'logout',
    icon: renderIcon(LogoutIcon)
  }
]

function handleMenuUpdate(key: string) {
  router.push({ name: key })
}

function handleUserSelect(key: string) {
  if (key === 'logout') {
    userStore.logout()
  }
}
</script>

<style scoped>
/* ---- Sidebar ---- */
.sidebar {
  background: #ffffff !important;
  border-right: 1px solid var(--color-border) !important;
  display: flex;
  flex-direction: column;
  padding-bottom: 12px;
}

/* Logo */
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--color-divider);
  overflow: hidden;
  white-space: nowrap;
  flex-shrink: 0;
}

.logo-collapsed {
  justify-content: center;
  padding: 0;
}

.logo-icon {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo-text {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text-1);
  letter-spacing: -0.5px;
}

/* Nav section */
.nav-section {
  flex: 1;
  padding: 10px 8px;
  overflow-y: auto;
}

:deep(.n-menu) {
  --n-item-height: 40px;
}

:deep(.n-menu-item-content) {
  border-radius: 10px !important;
  margin-bottom: 2px;
  transition: background 0.18s, color 0.18s;
}

/* Collapse trigger */
.sidebar-trigger {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 18px;
  cursor: pointer;
  color: var(--color-text-3);
  transition: color 0.2s;
  flex-shrink: 0;
}

.sidebar-trigger:hover {
  color: var(--color-primary);
}

.sidebar-trigger .n-icon {
  transition: transform 0.3s ease;
}

.sidebar-trigger.collapsed .n-icon {
  transform: rotate(180deg);
}

/* ---- Header ---- */
.header {
  height: 60px;
  background: #ffffff;
  border-bottom: 1px solid var(--color-divider);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
}

.breadcrumb :deep(.n-breadcrumb-item__link) {
  font-size: 13px;
  color: var(--color-text-3);
}

.breadcrumb :deep(.n-breadcrumb-item:last-child .n-breadcrumb-item__link) {
  color: var(--color-text-2);
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 12px 5px 6px;
  border-radius: 30px;
  border: 1.5px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  background: #fff;
}

.user-btn:hover {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(79,129,255,0.1);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--gradient-blue);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-2);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ---- Content ---- */
.content {
  background: var(--color-bg) !important;
  overflow-y: auto;
}

/* ---- Page transition ---- */
.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
