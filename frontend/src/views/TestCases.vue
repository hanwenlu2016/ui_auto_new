<template>
  <div class="test-cases-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>测试用例</h1>
        <p>管理和执行测试用例</p>
      </div>
      <n-space>
        <n-select
          v-model:value="selectedModuleId"
          :options="moduleOptions"
          placeholder="选择模块"
          style="width: 200px"
          @update:value="fetchTestCases"
        />
        <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedModuleId">
          <template #icon>
            <span style="font-size: 18px;">➕</span>
          </template>
          创建用例
        </n-button>
      </n-space>
    </div>

    <!-- Test Cases Table -->
    <n-card :bordered="false" class="table-card">
      <n-data-table
        :columns="columns"
        :data="testCases"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal" style="width: 800px">
      <n-card
        :title="editingId ? '编辑用例' : '创建用例'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        class="modal-card"
      >
        <n-form
          ref="formRef"
          :model="formValue"
          :rules="rules"
          label-placement="top"
        >
          <n-grid :cols="2" :x-gap="24">
            <n-form-item-grid-item label="用例名称" path="name">
              <n-input v-model:value="formValue.name" placeholder="请输入用例名称" />
            </n-form-item-grid-item>
            <n-form-item-grid-item label="优先级" path="priority">
              <n-select
                v-model:value="formValue.priority"
                :options="[
                  { label: 'P0', value: 'P0' },
                  { label: 'P1', value: 'P1' },
                  { label: 'P2', value: 'P2' }
                ]"
              />
            </n-form-item-grid-item>
          </n-grid>
          
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="请输入描述（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>

          <n-divider title-placement="left">测试步骤</n-divider>
          
          <n-dynamic-input
            v-model:value="formValue.steps"
            :on-create="onCreateStep"
            #="{ index, value }"
          >
            <div style="display: flex; gap: 12px; width: 100%; align-items: center;">
              <n-select
                v-model:value="value.page_id"
                :options="pageOptions"
                placeholder="选择页面"
                style="width: 150px"
                @update:value="(val) => fetchElementsForPage(val)"
              />
              <n-select
                v-model:value="value.element_id"
                :options="elementOptions.filter(e => e.page_id === value.page_id)"
                placeholder="选择元素"
                style="width: 150px"
                :disabled="!value.page_id"
              />
              <n-select
                v-model:value="value.action"
                :options="[
                  { label: '点击', value: 'click' },
                  { label: '输入', value: 'fill' },
                  { label: '跳转', value: 'goto' },
                  { label: '断言文本', value: 'assert_text' },
                  { label: '等待', value: 'wait' }
                ]"
                placeholder="操作"
                style="width: 120px"
              />
              <n-input v-model:value="value.value" placeholder="值 (Value)" style="flex: 1" />
            </div>
          </n-dynamic-input>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="handleCloseModal">取消</n-button>
            <n-button type="primary" @click="handleCreate">
              {{ editingId ? '更新' : '创建' }}
            </n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch } from 'vue'
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NDivider, NDynamicInput, NGrid, NFormItemGridItem, NTag } from 'naive-ui'
import api from '@/api'

interface TestCase {
  id: number
  name: string
  description: string
  priority: string
  module_id: number
  steps: any[]
  created_at: string
  updated_at: string
  creator_name: string
  updater_name: string
}

interface Module {
  id: number
  name: string
}

interface Page {
  id: number
  name: string
}

interface PageElement {
  id: number
  name: string
  page_id: number
}

const message = useMessage()
const loading = ref(false)
const testCases = ref<TestCase[]>([])
const modules = ref<Module[]>([])
const pages = ref<Page[]>([])
const elements = ref<PageElement[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const pageOptions = ref<{ label: string; value: number }[]>([])
const elementOptions = ref<{ label: string; value: number; page_id: number }[]>([])

const selectedModuleId = ref<number | null>(null)
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

const formValue = ref({
  name: '',
  description: '',
  priority: 'P1',
  steps: [] as { action: string; target: string; value: string; page_id?: number; element_id?: number }[]
})

const rules = {
  name: {
    required: true,
    message: '请输入用例名称',
    trigger: 'blur'
  }
}

const onCreateStep = () => {
  return {
    action: 'click',
    target: '',
    value: '',
    page_id: null,
    element_id: null
  }
}

const columns: DataTableColumns<TestCase> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  { 
    title: '优先级', 
    key: 'priority',
    width: 100,
    render(row) {
      const type = row.priority === 'P0' ? 'error' : row.priority === 'P1' ? 'warning' : 'info'
      return h(NTag, { type, size: 'small' }, { default: () => row.priority })
    }
  },
  { title: '描述', key: 'description' },
  { 
    title: '创建时间', 
    key: 'created_at',
    width: 180,
    render(row) {
      return row.created_at ? new Date(row.created_at).toLocaleString() : '-'
    }
  },
  { 
    title: '更新时间', 
    key: 'updated_at',
    width: 180,
    render(row) {
      return row.updated_at ? new Date(row.updated_at).toLocaleString() : '-'
    }
  },
  { title: '创建人', key: 'creator_name', width: 100 },
  { title: '更新人', key: 'updater_name', width: 100 },
  {
    title: '操作',
    key: 'actions',
    render(row) {
      return h(NSpace, null, {
        default: () => [
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              secondary: true,
              onClick: () => handleRun(row)
            },
            { default: () => '运行' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'primary',
              secondary: true,
              onClick: () => handleEdit(row)
            },
            { default: () => '编辑' }
          ),
          h(
            NButton,
            {
              size: 'small',
              type: 'error',
              secondary: true,
              onClick: () => handleDelete(row)
            },
            { default: () => '删除' }
          )
        ]
      })
    }
  }
]

const pagination = { pageSize: 10 }

const fetchModules = async () => {
  try {
    const response = await api.get('/modules/')
    modules.value = response.data
    moduleOptions.value = modules.value.map(m => ({
      label: m.name,
      value: m.id
    }))
    if (modules.value.length > 0 && !selectedModuleId.value) {
      selectedModuleId.value = modules.value[0].id
    }
  } catch (error) {
    message.error('获取模块列表失败')
  }
}

const fetchPages = async () => {
  if (!selectedModuleId.value) {
    pages.value = []
    pageOptions.value = []
    return
  }
  try {
    const response = await api.get(`/pages/?module_id=${selectedModuleId.value}`)
    pages.value = response.data
    pageOptions.value = pages.value.map(p => ({
      label: p.name,
      value: p.id
    }))
  } catch (error) {
    message.error('获取页面列表失败')
  }
}

// Fetch all elements for the module (via pages) or just fetch all elements and filter locally?
// Better to fetch elements by page when page is selected, but for editing existing steps we might need all.
// Let's fetch all elements for the module's pages.
// Actually, the API supports filtering by module_id? No, we removed it.
// We need to fetch elements by page_id.
// Strategy: When a page is selected in a step, fetch elements for that page if not already fetched?
// Or just pre-fetch all elements for all pages in the module?
// Let's keep it simple: fetch all elements for the current module's pages.
// We'll need a new API endpoint or just loop through pages.
// For now, let's just fetch elements when a page is selected in the UI.
// But we need a way to populate the options.
// Let's add a helper to fetch elements for a specific page.

const fetchElementsForPage = async (pageId: number) => {
  try {
    const response = await api.get(`/elements/?page_id=${pageId}`)
    const newElements = response.data
    // Merge into elements list avoiding duplicates
    newElements.forEach((e: PageElement) => {
      if (!elements.value.find(el => el.id === e.id)) {
        elements.value.push(e)
      }
    })
    updateElementOptions()
  } catch (error) {
    console.error('Failed to fetch elements', error)
  }
}

const updateElementOptions = () => {
  elementOptions.value = elements.value.map(e => ({
    label: e.name,
    value: e.id,
    page_id: e.page_id
  }))
}

const fetchTestCases = async () => {
  if (!selectedModuleId.value) return
  loading.value = true
  try {
    const response = await api.get(`/cases/?module_id=${selectedModuleId.value}`)
    testCases.value = response.data
  } catch (error) {
    message.error('获取测试用例列表失败')
  } finally {
    loading.value = false
  }
}

watch(selectedModuleId, async () => {
  await fetchPages()
  fetchTestCases()
  // Clear elements when module changes
  elements.value = []
  updateElementOptions()
})

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedModuleId.value) {
      try {
        const data = { ...formValue.value, module_id: selectedModuleId.value }
        if (editingId.value) {
          await api.put(`/cases/${editingId.value}`, data)
          message.success('用例更新成功')
        } else {
          await api.post('/cases/', data)
          message.success('用例创建成功')
        }
        handleCloseModal()
        fetchTestCases()
      } catch (error) {
        message.error(editingId.value ? '更新用例失败' : '创建用例失败')
      }
    }
  })
}

const handleRun = async (row: TestCase) => {
  try {
    const response = await api.post(`/execution/cases/${row.id}/run`)
    const data = response.data
    
    // 显示后端返回的消息
    message.success(data.message || '测试已启动,请到测试报告页面查看执行结果')
    
  } catch (error) {
    message.error('启动测试失败')
  }
}

const handleEdit = async (row: TestCase) => {
  editingId.value = row.id
  // We need to ensure we have the pages and elements loaded for this case's module
  // But selectedModuleId might be different.
  // Ideally we should switch to the case's module or just load data.
  // For simplicity, assume we are in the correct module view.
  
  // Pre-load elements for pages used in steps
  if (row.steps) {
    for (const step of row.steps) {
      if (step.page_id) {
        await fetchElementsForPage(step.page_id)
      }
    }
  }

  formValue.value = {
    name: row.name,
    description: row.description,
    priority: row.priority,
    steps: row.steps ? row.steps.map(s => ({...s})) : []
  }
  showCreateModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  formValue.value = { name: '', description: '', priority: 'P1', steps: [] }
  editingId.value = null
}

const handleDelete = async (row: TestCase) => {
  try {
    await api.delete(`/cases/${row.id}`)
    message.success('Test case deleted successfully')
    fetchTestCases()
  } catch (error) {
    message.error('Failed to delete test case')
  }
}

onMounted(() => {
  fetchModules()
})
</script>
