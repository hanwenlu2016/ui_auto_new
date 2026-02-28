---
name: vue-component
description: 在本项目中创建标准的 Vue 3 + TypeScript 组件，使用 Naive UI 组件库、Pinia 状态管理，遵循项目现有架构模式。
---

# Vue 3 组件创建规范

## 项目前端架构说明

```
frontend/src/
├── views/          # 页面级组件 (对应路由)
├── components/     # 可复用组件
├── stores/         # Pinia 状态管理
├── api/            # API 请求层
├── router/         # 路由配置
└── types/          # TypeScript 类型定义
```

## 技术栈

- **UI 框架**: Vue 3 Composition API + `<script setup>` 语法
- **UI 组件库**: Naive UI (`n-*` 组件)
- **状态管理**: Pinia
- **HTTP 客户端**: Axios（封装在 `src/api/` 中）
- **语言**: TypeScript

## 创建新页面/组件的步骤

### 1. 在 `src/api/` 添加 API 请求函数

```typescript
// src/api/resource.ts
import axios from './index'
import type { Resource, ResourceCreate, ResourceUpdate } from '@/types/resource'

export const resourceApi = {
  getList: () => axios.get<Resource[]>('/resources/'),
  getById: (id: number) => axios.get<Resource>(`/resources/${id}`),
  create: (data: ResourceCreate) => axios.post<Resource>('/resources/', data),
  update: (id: number, data: ResourceUpdate) => axios.put<Resource>(`/resources/${id}`, data),
  delete: (id: number) => axios.delete(`/resources/${id}`),
}
```

### 2. 在 `src/types/` 添加 TypeScript 类型

```typescript
// src/types/resource.ts
export interface Resource {
  id: number
  name: string
  description?: string
  created_at: string
}

export interface ResourceCreate {
  name: string
  description?: string
}

export interface ResourceUpdate {
  name?: string
  description?: string
}
```

### 3. 在 `src/stores/` 创建 Pinia Store（如需全局状态）

```typescript
// src/stores/resource.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { resourceApi } from '@/api/resource'
import type { Resource } from '@/types/resource'

export const useResourceStore = defineStore('resource', () => {
  const list = ref<Resource[]>([])
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      const { data } = await resourceApi.getList()
      list.value = data
    } finally {
      loading.value = false
    }
  }

  return { list, loading, fetchList }
})
```

### 4. 创建 View 组件（页面级）

```vue
<!-- src/views/ResourceView.vue -->
<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import {
  NDataTable, NButton, NSpace, NModal, NForm, NFormItem,
  NInput, useMessage, type DataTableColumns
} from 'naive-ui'
import { resourceApi } from '@/api/resource'
import type { Resource } from '@/types/resource'

const message = useMessage()
const loading = ref(false)
const tableData = ref<Resource[]>([])
const showModal = ref(false)

// 表格列定义
const columns: DataTableColumns<Resource> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  { title: '描述', key: 'description' },
  {
    title: '操作',
    key: 'actions',
    render: (row) => h(NSpace, null, {
      default: () => [
        h(NButton, { size: 'small', type: 'primary', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
        h(NButton, { size: 'small', type: 'error', onClick: () => handleDelete(row.id) }, { default: () => '删除' }),
      ]
    })
  }
]

// 获取数据
async function fetchData() {
  loading.value = true
  try {
    const { data } = await resourceApi.getList()
    tableData.value = data
  } catch (e) {
    message.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

function handleEdit(row: Resource) {
  // 打开编辑弹窗
  showModal.value = true
}

async function handleDelete(id: number) {
  try {
    await resourceApi.delete(id)
    message.success('删除成功')
    await fetchData()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(() => fetchData())
</script>

<template>
  <div class="resource-view">
    <n-space justify="space-between" style="margin-bottom: 16px">
      <h2>资源管理</h2>
      <n-button type="primary" @click="showModal = true">新建</n-button>
    </n-space>

    <n-data-table
      :columns="columns"
      :data="tableData"
      :loading="loading"
      :row-key="(row) => row.id"
    />

    <!-- 新建/编辑弹窗 -->
    <n-modal v-model:show="showModal" title="新建资源" preset="dialog">
      <!-- 表单内容 -->
    </n-modal>
  </div>
</template>
```

### 5. 在 `router/index.ts` 注册路由

```typescript
{
  path: '/resources',
  name: 'Resources',
  component: () => import('@/views/ResourceView.vue'),
  meta: { title: '资源管理' }
}
```

## 规范要点

- **始终使用** `<script setup>` 语法糖
- **类型安全**: 所有 props、emits、ref 都必须有 TypeScript 类型
- **Naive UI**: 使用 `useMessage()` 显示操作反馈，而非 `alert()`
- **错误处理**: API 调用必须有 try/catch，并显示用户友好的错误提示
- **Loading 状态**: 数据加载时设置 `loading.value = true`
- **组件命名**: 页面组件以 `View` 结尾，可复用组件以功能命名
- **样式**: 使用 scoped CSS，类名使用 kebab-case
