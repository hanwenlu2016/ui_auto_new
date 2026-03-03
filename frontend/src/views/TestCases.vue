<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1>测试用例</h1>
        <p>管理和执行模块下的测试用例</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="项目"
          style="width: 160px"
          @update:value="handleProjectChange"
        />
        <n-select
          v-model:value="selectedModuleId"
          :options="moduleOptions"
          placeholder="模块"
          style="width: 180px"
          @update:value="fetchTestCases"
          clearable
        />
        <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedModuleId">
          <template #icon>
            <span style="font-size: 16px;">➕</span>
          </template>
          创建用例
        </n-button>
      </div>
    </div>

    <!-- Test Cases Table -->
    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s">
      <n-data-table
        :columns="columns"
        :data="testCases"
        :loading="loading"
        :pagination="pagination"
      />
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal">
      <n-card
        style="width: 800px; max-width: 90vw;"
        :title="editingId ? '✏️ 编辑测试用例' : '➕ 创建测试用例'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <n-form
          ref="formRef"
          :model="formValue"
          :rules="rules"
          label-placement="top"
        >
          <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 20px;">
            <n-form-item label="用例名称" path="name">
              <n-input v-model:value="formValue.name" placeholder="简要描述测试目的" />
            </n-form-item>
            <n-form-item label="优先级" path="priority">
              <n-select
                v-model:value="formValue.priority"
                :options="[
                  { label: 'P0 核心', value: 'P0' },
                  { label: 'P1 重要', value: 'P1' },
                  { label: 'P2 一般', value: 'P2' }
                ]"
              />
            </n-form-item>
          </div>
          
          <n-form-item label="详细描述 (可选)" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="添加前提条件、前置数据等信息..."
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>

          <div style="display: flex; align-items: center; justify-content: space-between; margin: 24px 0 16px 0;">
             <div style="font-weight: 600; font-size: 15px; color: var(--color-text-1);">测试步骤定义</div>
             <n-button round type="primary" ghost size="small" @click="showAIModal = true">
               ✨ AI 智能生成
             </n-button>
          </div>
          
          <div style="background: var(--color-bg); padding: 16px; border-radius: 12px; border: 1px solid var(--color-divider);">
            <n-dynamic-input
              v-model:value="formValue.steps"
              :on-create="onCreateStep"
              #="{ index, value }"
            >
              <div style="display: flex; gap: 10px; width: 100%; align-items: center;">
                <n-tag type="info" size="small" :bordered="false" style="width: 24px; justify-content: center; font-weight: 600;">{{ index + 1 }}</n-tag>
                <n-select
                  v-model:value="value.page_id"
                  :options="pageOptions"
                  placeholder="页面上下文"
                  style="width: 140px"
                  @update:value="(val) => fetchElementsForPage(val)"
                />
                <n-select
                  v-model:value="value.element_id"
                  :options="elementOptions.filter(e => e.page_id === value.page_id)"
                  placeholder="目标元素"
                  style="width: 150px"
                  :disabled="!value.page_id"
                  clearable
                />
                <n-select
                  v-model:value="value.action"
                  :options="[
                    { label: '🖱️ 点击', value: 'click' },
                    { label: '⌨️ 输入', value: 'fill' },
                    { label: '🔗 跳转', value: 'goto' },
                    { label: '✅ 断言', value: 'assert_text' },
                    { label: '⏳ 等待', value: 'wait' }
                  ]"
                  placeholder="操作"
                  style="width: 130px"
                />
                <n-input v-model:value="value.value" placeholder="参数 (Value)" style="flex: 1" />
              </div>
            </n-dynamic-input>
            <div v-if="formValue.steps.length === 0" style="text-align: center; color: var(--color-text-3); padding: 12px 0; font-size: 13px;">
              暂无步骤，点击右侧添加按钮或使用AI生成
            </div>
          </div>
        </n-form>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="handleCloseModal">取消</n-button>
            <n-button type="primary" @click="handleCreate">
              {{ editingId ? '保存更改' : '确认创建' }}
            </n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
    
    <!-- AI Generation Modal -->
    <n-modal v-model:show="showAIModal">
      <n-card
        title="✨ AI 智能解析步骤"
        :bordered="false"
        size="large"
        role="dialog"
        aria-modal="true"
        style="width: 500px;"
      >
        <div style="margin-bottom: 20px;">
           <p style="color: var(--color-text-2); font-size: 13px; line-height: 1.6; margin-bottom: 16px;">
             使用自然语言描述连续动作，AI 将自动将其转化为标准化的执行步骤。<br/>
             <span style="color: var(--color-text-3); font-size: 12px;">💡 提示：描述越明确（包含页面元素名称和输入值），生成的质量越高。</span>
           </p>
           <n-input
             v-model:value="aiPrompt"
             type="textarea"
             placeholder="示例: 打开百度首页，在搜索框输入 'Vue3'，然后点击百度一下按钮"
             :rows="4"
             style="background: var(--color-bg);"
           />
        </div>
        
        <div v-if="aiLoading" style="text-align: center; margin: 30px 0;">
          <n-spin size="medium" />
          <div style="margin-top: 12px; color: var(--color-primary); font-size: 13px;">AI 大脑正在飞速运转中...</div>
        </div>
        
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="showAIModal = false" :disabled="aiLoading">取消</n-button>
            <n-button 
              type="primary" 
              @click="handleGenerateSteps" 
              :disabled="!aiPrompt || aiLoading"
              :loading="aiLoading"
            >
              一键生成
            </n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch } from 'vue'
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NDynamicInput, NTag, NSpin } from 'naive-ui'
import api from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

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

const message = useMessage()
const loading = ref(false)
const testCases = ref<TestCase[]>([])
const projects = ref<any[]>([])
const modules = ref<any[]>([])
const pages = ref<any[]>([])
const elements = ref<any[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const pageOptions = ref<{ label: string; value: number }[]>([])
const elementOptions = ref<{ label: string; value: number; page_id: number }[]>([])

const selectedProjectId = ref<number | null>(appStore.selectedProjectId)
const selectedModuleId = ref<number | null>(appStore.selectedModuleId)
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

const formValue = ref({
  name: '',
  description: '',
  priority: 'P1',
  steps: [] as any[]
})

// AI Generation State
const showAIModal = ref(false)
const aiPrompt = ref('')
const aiLoading = ref(false)

const rules = {
  name: { required: true, message: '请输入用例名称', trigger: 'blur' }
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
  { title: '用例名称', key: 'name', minWidth: 200 },
  { 
    title: '优先级', 
    key: 'priority',
    width: 90,
    render(row) {
      if (row.priority === 'P0') return h('span', { class: 'badge badge-p0' }, 'P0')
      if (row.priority === 'P1') return h('span', { class: 'badge badge-p1' }, 'P1')
      return h('span', { class: 'badge badge-p2' }, row.priority || 'P2')
    }
  },
  { title: '步骤数', key: 'steps', width: 80, render: (row) => row.steps?.length || 0 },
  { 
    title: '最近更新', 
    key: 'updated_at',
    width: 160,
    render(row) {
      const d = row.updated_at || row.created_at
      return d ? new Date(d).toLocaleString() : '-'
    }
  },
  { title: '维护人', key: 'updater_name', width: 120, render: (row) => row.updater_name || row.creator_name || '-' },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right' as const,
    render(row) {
      return h(NSpace, { align: 'center', wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', type: 'primary', onClick: () => handleRun(row) }, { default: () => '执行' }),
          h(NButton, { size: 'small', tertiary: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', tertiary: true, type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
    }
  }
]

const pagination = { pageSize: 15 }

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
    projectOptions.value = projects.value.map(p => ({ label: p.name, value: p.id }))
    if (projects.value.length > 0 && !selectedProjectId.value) {
      selectedProjectId.value = projects.value[0].id
      appStore.setProjectId(selectedProjectId.value)
    }
    if (selectedProjectId.value) await fetchModules(selectedProjectId.value)
  } catch (error) {
    message.error('获取项目列表失败')
  }
}

const fetchModules = async (projectId: number | null) => {
  if (!projectId) {
    moduleOptions.value = []
    return
  }
  try {
    const response = await api.get(`/modules/?project_id=${projectId}`)
    modules.value = response.data
    moduleOptions.value = modules.value.map(m => ({ label: m.name, value: m.id }))
    
    // If selectedModuleId is set but not in this project, or not set, default it
    if (moduleOptions.value.length > 0) {
      if (!selectedModuleId.value || !moduleOptions.value.find(m => m.value === selectedModuleId.value)) {
        selectedModuleId.value = moduleOptions.value[0].value
        appStore.setModuleId(selectedModuleId.value)
      }
    } else {
      selectedModuleId.value = null
      appStore.setModuleId(null)
    }
    fetchTestCases()
  } catch (error) {
    message.error('获取模块列表失败')
  }
}

const handleProjectChange = (val: number | null) => {
  selectedProjectId.value = val
  appStore.setProjectId(val)
  selectedModuleId.value = null
  appStore.setModuleId(null)
  fetchModules(val)
}

const fetchPages = async () => {
  if (!selectedModuleId.value) {
    pageOptions.value = []
    return
  }
  try {
    const response = await api.get(`/pages/?module_id=${selectedModuleId.value}`)
    pages.value = response.data
    pageOptions.value = pages.value.map(p => ({ label: p.name, value: p.id }))
  } catch (error) {}
}

const fetchElementsForPage = async (pageId: number) => {
  try {
    const response = await api.get(`/elements/?page_id=${pageId}`)
    const newElements = response.data
    newElements.forEach((e: any) => {
      if (!elements.value.find(el => el.id === e.id)) {
        elements.value.push(e)
      }
    })
    updateElementOptions()
  } catch (error) {}
}

const updateElementOptions = () => {
  elementOptions.value = elements.value.map(e => ({
    label: e.name,
    value: e.id,
    page_id: e.page_id
  }))
}

const fetchTestCases = async () => {
  loading.value = true
  try {
    const url = selectedModuleId.value ? `/cases/?module_id=${selectedModuleId.value}` : '/cases/'
    const response = await api.get(url)
    testCases.value = response.data
  } catch (error) {
    message.error('获取用例列表失败')
  } finally {
    loading.value = false
  }
}

watch(selectedModuleId, async (val) => {
  appStore.setModuleId(val)
  await fetchPages()
  fetchTestCases()
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
          message.success('用例修改成功')
        } else {
          await api.post('/cases/', data)
          message.success('用例创建成功')
        }
        handleCloseModal()
        fetchTestCases()
      } catch (error: any) {
        const d = error?.response?.data?.detail
        message.error(d ? `保存失败：${d}` : '操作失败')
      }
    }
  })
}

const handleRun = async (row: TestCase) => {
  try {
    message.info('准备执行测试引擎...')
    const response = await api.post(`/execution/cases/${row.id}/run`)
    message.success(response.data.message || '测试任务已触发，请查看报告')
  } catch (error) {
    message.error('触发测试执行失败')
  }
}

const handleEdit = async (row: TestCase) => {
  editingId.value = row.id
  if (row.steps) {
    for (const step of row.steps) {
      if (step.page_id) await fetchElementsForPage(step.page_id)
    }
  }
  formValue.value = {
    name: row.name,
    description: row.description,
    priority: row.priority || 'P1',
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
    message.success('已删除用例')
    fetchTestCases()
  } catch (error) {}
}

const handleGenerateSteps = async () => {
  if (!aiPrompt.value) return
  aiLoading.value = true
  try {
    const response = await api.post('/ai/generate', { prompt: aiPrompt.value })
    const generatedSteps = response.data.steps
    if (generatedSteps && generatedSteps.length > 0) {
      const newSteps = generatedSteps.map((s: any) => ({
        action: s.action,
        target: s.target || s.selector || '', 
        value: s.value || '',
        page_id: null,
        element_id: null
      }))
      formValue.value.steps = [...formValue.value.steps, ...newSteps]
      message.success(`成功解析并添加 ${newSteps.length} 个步骤`)
      showAIModal.value = false
      aiPrompt.value = ''
    } else {
      message.warning('未生成步骤，请尝试换种描述')
    }
  } catch (error) {
    message.error('AI 解析异常')
  } finally {
    aiLoading.value = false
  }
}

onMounted(() => fetchProjects())
</script>

<style scoped>
.card-wrap {
  background: var(--color-card);
  border-radius: 16px;
  border: 1px solid var(--color-divider);
  padding: 4px; /* DataTable component natively provides padding */
  overflow: hidden;
}
</style>
