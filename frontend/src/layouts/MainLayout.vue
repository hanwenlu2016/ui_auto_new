<template>
  <n-layout has-sider style="height: 100vh">
    <n-layout-sider
      bordered
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      :collapsed="collapsed"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="logo">
        UI Auto
      </div>
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="22"
        :options="menuOptions"
        :value="activeKey"
        @update:value="handleMenuUpdate"
      />
    </n-layout-sider>
    <n-layout>
      <n-layout-header bordered class="header">
        <div class="header-content">
          <n-breadcrumb>
            <n-breadcrumb-item>Home</n-breadcrumb-item>
            <n-breadcrumb-item>{{ currentRouteName }}</n-breadcrumb-item>
          </n-breadcrumb>
          <div class="user-profile">
            <n-dropdown :options="userOptions" @select="handleUserSelect">
              <n-button text>
                {{ userStore.user?.full_name || 'User' }}
                <template #icon>
                  <n-icon>
                    <person-icon />
                  </n-icon>
                </template>
              </n-button>
            </n-dropdown>
          </div>
        </div>
      </n-layout-header>
      <n-layout-content>
        <router-view />
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { h, ref, computed, Component } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  NIcon, 
  NLayout, 
  NLayoutSider, 
  NLayoutHeader, 
  NLayoutContent, 
  NMenu, 
  NBreadcrumb, 
  NBreadcrumbItem, 
  NDropdown, 
  NButton 
} from 'naive-ui'
import type { MenuOption } from 'naive-ui'
import {
  HomeOutline as HomeIcon,
  FolderOutline as ProjectIcon,
  GridOutline as ModuleIcon,
  ListOutline as CaseIcon,
  VideocamOutline as RecordIcon,
  PersonOutline as PersonIcon,
  LogOutOutline as LogoutIcon,
  List as ListIcon,
  DocumentTextOutline as ReportIcon
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
    label: '项目',
    key: 'Projects',
    icon: renderIcon(ProjectIcon)
  },
  {
    label: '模块',
    key: 'Modules',
    icon: renderIcon(ModuleIcon)
  },
  {
    label: '页面',
    key: 'Pages',
    icon: renderIcon(ListIcon)
  },
  {
    label: '测试用例',
    key: 'TestCases',
    icon: renderIcon(CaseIcon)
  },
  {
    label: '页面元素',
    key: 'PageElements',
    icon: renderIcon(ListIcon)
  },
  {
    label: '测试套件',
    key: 'TestSuites',
    icon: renderIcon(ListIcon)
  },
  {
    label: '录制',
    key: 'Recording',
    icon: renderIcon(RecordIcon)
  },
  {
    label: '报告',
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
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #2d8cf0;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.3s ease;
  overflow: hidden;
  white-space: nowrap;
}

:deep(.n-layout-sider) {
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  z-index: 10;
}

.header {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 9;
}

.header-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.user-profile {
  display: flex;
  align-items: center;
}

:deep(.n-layout-content) {
  background: #f0f2f5;
}

:deep(.n-breadcrumb-item__link) {
  color: #666;
}

:deep(.n-breadcrumb-item:last-child .n-breadcrumb-item__link) {
  color: #333;
  font-weight: normal;
}
</style>
