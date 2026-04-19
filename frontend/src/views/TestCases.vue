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
    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s; padding: 0;">
      <n-data-table
        :columns="columns"
        :data="testCases"
        :loading="loading"
        :pagination="pagination"
        size="small"
        :bordered="false"
        class="custom-table"
      />
    </div>

    <n-modal v-model:show="showCreateModal">
      <n-card
        style="width: 1100px; max-width: 95vw;"
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
              show-sort-button
            >
              <template #default="{ index, value }">
                <div style="display: flex; gap: 8px; width: 100%; align-items: center;">
                  <n-tag :bordered="false" type="info" size="small" style="width: 28px; justify-content: center; font-weight: 700; background: rgba(var(--color-primary-rgb), 0.1);">
                    {{ index + 1 }}
                  </n-tag>
                  
                  <!-- Element Strategy Toggle -->
                  <div style="display: flex; align-items: center; border-right: 1px solid var(--color-divider); padding-right: 8px; margin-right: 8px;">
                    <n-tooltip trigger="hover">
                      <template #trigger>
                        <n-button
                          quaternary
                          circle
                          size="small"
                          :type="value._custom_locator_mode ? 'warning' : 'primary'"
                          @click="value._custom_locator_mode = !value._custom_locator_mode"
                        >
                          {{ value._custom_locator_mode ? '🎯' : '🗂️' }}
                        </n-button>
                      </template>
                      {{ value._custom_locator_mode ? '切换到元素库 (选择已有元素)' : '切换到自定义定位 (直接编写XPath/CSS)' }}
                    </n-tooltip>
                  </div>

                  <template v-if="!value._custom_locator_mode">
                    <!-- Page & Element context (Compact) -->
                    <n-select
                      v-model:value="value.page_id"
                      :options="pageOptions"
                      placeholder="页面"
                      style="width: 100px"
                      @update:value="(val) => fetchElementsForPage(val)"
                    />
                    <n-select
                      v-model:value="value.element_id"
                      :options="elementOptions.filter(e => e.page_id === value.page_id)"
                      placeholder="目标元素"
                      style="width: 120px"
                      :disabled="!value.page_id"
                      clearable
                      @update:value="(v) => { if (v) { value.target = ''; value.selector = ''; } }"
                    />
                    
                    <!-- Edit Button for Bound Element -->
                    <n-button 
                      v-if="value.element_id"
                      quaternary 
                      circle 
                      size="small" 
                      type="info" 
                      @click="handleOpenElementModal(index, true)" 
                      title="编辑库内元素"
                    >
                      <template #icon><span>✏️</span></template>
                    </n-button>
                  </template>
                  <template v-else>
                    <!-- Custom Locator Mode: Button trigger -->
                    <n-button
                       dashed
                       type="primary"
                       size="medium"
                       style="width: 228px; justify-content: flex-start; padding: 0 12px; font-weight: 500;"
                       @click="handleOpenElementModal(index, false)"
                    >
                       <template #icon><span style="margin-right: 4px;">🎯</span></template>
                       <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                         {{ value.target || '配置自定义定位' }}
                       </span>
                    </n-button>
                  </template>
                  
                  <!-- Action & Value -->
                  <n-select
                    v-model:value="value.action"
                    :options="[
                      { label: '🖱️ 点击', value: 'click' },
                      { label: '⌨️ 输入', value: 'fill' },
                      { label: '🪄 按键', value: 'press' },
                      { label: '🖐️ 悬停', value: 'hover' },
                      { label: '📑 下拉选择', value: 'select' },
                      { label: '🔗 跳转', value: 'goto' },
                      { label: '✅ 断言', value: 'assert_text' },
                      { label: '👀 断言可见', value: 'assert_visible' },
                      { label: '⏳ 等待', value: 'wait' },
                      { label: '⏳ 等待元素', value: 'wait_for_selector' },
                      { label: '📸 截图', value: 'screenshot' },
                      { label: '📋 提取文本', value: 'get_text' },
                      { label: '🆔 提取属性', value: 'get_attribute' },
                      { label: '⚙️ 设置变量', value: 'set_variable' }
                    ]"
                    placeholder="动作"
                    style="width: 110px"
                  />
                  
                  <n-input v-model:value="value.value" placeholder="参数 / 表达式" style="flex: 1" />
                  
                  <!-- Variable Output -->
                  <n-input 
                    v-model:value="value.variable_name" 
                    placeholder="变量名 $" 
                    style="width: 100px"
                  >
                    <template #prefix>
                      <span style="font-size: 11px; color: var(--color-primary); font-weight: 700;">$</span>
                    </template>
                  </n-input>
                </div>
              </template>
              
              <template #action="{ index, create, remove }">
                <div style="display: flex; gap: 4px; margin-left: 8px;">
                  <n-button quaternary circle size="small" type="error" @click="remove(index)">
                    <template #icon><span>🗑️</span></template>
                  </n-button>
                  <n-button quaternary circle size="small" type="primary" @click="create(index)">
                    <template #icon><span>➕</span></template>
                  </n-button>
                </div>
              </template>
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
        style="width: 700px;"
      >
        <div style="margin-bottom: 20px;">
           <p style="color: var(--color-text-2); font-size: 13px; line-height: 1.6; margin-bottom: 12px;">
             使用自然语言描述连续动作，AI 将自动将其转化为标准化的执行步骤。<br/>
             <span style="color: var(--color-text-3); font-size: 12px;">💡 提示：描述越明确（包含页面元素名称和输入值），生成的质量越高。</span>
           </p>
           
           <div style="display: flex; gap: 12px; margin-bottom: 12px; align-items: center; justify-content: space-between;">
             <div style="display: flex; gap: 12px; align-items: center;">
               <span style="font-size: 13px; color: var(--color-text-2); font-weight: 500;">引擎选择:</span>
               <n-select
                 v-model:value="selectedAIModel"
                 :options="aiModelOptions"
                 style="width: 160px"
                 size="small"
                 placeholder="加载模型中..."
               />
             </div>
             
              <div style="display: flex; align-items: center; gap: 8px;">
                <span 
                  @click="agentMode = false"
                  :style="{ fontSize: '13px', cursor: 'pointer', userSelect: 'none', color: !agentMode ? 'var(--color-primary)' : 'var(--color-text-3)', fontWeight: !agentMode ? '600' : '400' }"
                >快速</span>
                <n-switch v-model:value="agentMode" size="small" />
                <span 
                  @click="agentMode = true"
                  :style="{ fontSize: '13px', cursor: 'pointer', userSelect: 'none', color: agentMode ? 'var(--color-primary)' : 'var(--color-text-3)', fontWeight: agentMode ? '600' : '400' }"
                >精准</span>
              </div>
           </div>

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
          <div style="margin-top: 12px; color: var(--color-primary); font-size: 13px;">
            {{ agentMode ? 'Agent 正在浏览器中执行并验证...' : 'AI 大脑正在飞速运转中...' }}
          </div>
          <div v-if="agentMode" style="margin-top: 8px; font-size: 12px; color: var(--color-text-3);">
            实时步骤已在编辑器背景中同步生成
          </div>
        </div>
        
        <!-- Footer -->
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
    
    <!-- Unified Inline Element Editor Modal -->
    <n-modal v-model:show="showElementModal">
      <n-card
        style="width: 650px; max-width: 90vw"
        :title="elementIsLibraryMode ? '✏️ 编辑库内元素' : '🎯 配置自定义定位'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <div v-if="!elementIsLibraryMode" style="margin-bottom: 20px;">
          <n-alert type="info" :show-icon="false" style="border-radius: 8px;">
            <template #default>
              <div>当前处于 <strong>自定义定位模式</strong>。</div>
              <div style="font-size: 13px; color: var(--color-text-2); margin-top: 4px;">
                您可以直接修改 AI 生成的或手写的定位符。此修改<strong>仅作用于当前步骤</strong>，不影响项目公用元素库。
              </div>
            </template>
          </n-alert>
        </div>

        <n-form
          ref="elementFormRef"
          :model="elementFormValue"
          :rules="elementRules"
          label-placement="top"
        >
          <n-form-item label="元素说明 / 标识" path="name">
            <n-input v-model:value="elementFormValue.name" placeholder="例如：登录按钮、搜索框" />
          </n-form-item>
          <n-form-item v-if="elementIsLibraryMode" label="元素描述" path="description">
            <n-input
              v-model:value="elementFormValue.description"
              type="textarea"
              placeholder="添加补充说明（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
          
          <div style="background: var(--color-bg); padding: 16px 20px; border-radius: 12px; margin-top: 8px;">
            <div style="font-weight: 500; font-size: 13px; color: var(--color-text-2); margin-bottom: 12px;">定位规则配置</div>
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 16px;">
              <n-form-item label="定位方式" path="locator_type" style="margin-bottom: 0;">
                <n-select
                  v-model:value="elementFormValue.locator_type"
                  :options="locatorOptions"
                  placeholder="选择方式"
                />
              </n-form-item>
              <n-form-item label="定位特征值" path="locator_value" style="margin-bottom: 0;">
                <n-input v-model:value="elementFormValue.locator_value" placeholder="例如: #login-btn 或 //*[@id='app']" />
              </n-form-item>
            </div>
          </div>
        </n-form>
        
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="showElementModal = false">取消</n-button>
            <n-button type="primary" @click="handleSaveElement">
              {{ elementIsLibraryMode ? '保存并同步到库' : '确认配置' }}
            </n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch } from 'vue'
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NDynamicInput, NTag, NSpin, NAlert, NTooltip } from 'naive-ui'
import api from '@/api'
import { useAppStore } from '@/stores/app'
import { bindGeneratedStepsToKnownElements, loadAiContext } from '@/utils/aiContext'

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
const aiModelOptions = ref<any[]>([])
const selectedAIModel = ref<string | null>(null)
const agentMode = ref(false) // Toggle between Fast (AIService) and Precision (AgentService)

const rules = {
  name: { required: true, message: '请输入用例名称', trigger: 'blur' }
}

const locatorOptions = [
  { label: 'XPath', value: 'xpath' },
  { label: 'CSS Selector', value: 'css' },
  { label: 'ID', value: 'id' },
  { label: 'Name', value: 'name' },
  { label: 'Class Name', value: 'class_name' },
  { label: 'Link Text', value: 'link_text' }
]

// Element Editor Modal State
const showElementModal = ref(false)
const elementFormRef = ref<FormInst | null>(null)
const elementIsLibraryMode = ref(false)
const editingStepIndex = ref<number | null>(null)

const elementFormValue = ref({
  id: null as number | null,
  name: '',
  description: '',
  locator_type: 'xpath',
  locator_value: ''
})

const elementRules = {
  name: { required: true, message: '请输入标识或名称', trigger: 'blur' },
  locator_type: { required: true, message: '请选择定位方式', trigger: 'change' },
  locator_value: { required: true, message: '请输入定位特征值', trigger: 'blur' }
}

const onCreateStep = () => {
  return {
    action: 'click',
    target: '',
    value: '',
    page_id: null,
    element_id: null,
    variable_name: '',
    _custom_locator_mode: false
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
      return h(NSpace, { align: 'center', wrap: false, size: 8 }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleRun(row) }, { default: () => '执行' }),
          h(NButton, { size: 'small', quaternary: true, onClick: () => handleEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
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

const fetchAIModels = async () => {
  try {
    const res = await api.get('/ai-models/')
    const activeModels = res.data.filter((m: any) => m.is_active)
    aiModelOptions.value = activeModels.map((m: any) => ({
      label: m.is_default ? `${m.name} (默认)` : m.name,
      value: String(m.id)  // Pass ID as string to backend request
    }))
    
    // Set default model
    const defaultModel = activeModels.find((m: any) => m.is_default)
    if (defaultModel) {
      selectedAIModel.value = String(defaultModel.id)
    } else if (activeModels.length > 0) {
      selectedAIModel.value = String(activeModels[0].id)
    }
  } catch (error) {
    console.error('Failed to fetch AI models', error)
  }
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
    steps: row.steps ? row.steps.map(s => ({
      ...s,
      _custom_locator_mode: !s.element_id && (s.target || s.selector) ? true : false
    })) : []
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

const handleOpenElementModal = async (stepIndex: number, isLibraryMode: boolean) => {
  editingStepIndex.value = stepIndex
  elementIsLibraryMode.value = isLibraryMode
  const step = formValue.value.steps[stepIndex]

  if (isLibraryMode) {
    if (!step.element_id) return
    const elId = step.element_id
    try {
      // First, get it from local list if available
      let elData = elements.value.find(e => e.id === elId)
      if (!elData) {
        const response = await api.get(`/elements/${elId}`)
        elData = response.data
      }
      if (elData) {
        elementFormValue.value = {
          id: elData.id,
          name: elData.name,
          description: elData.description || '',
          locator_type: elData.locator_type,
          locator_value: elData.locator_value
        }
      }
    } catch (e) {
      message.error('无法获取元素详情')
      return
    }
  } else {
    // Custom locator mode
    let locType = step.locator_type || 'xpath'
    const targetVal = step.target || step.selector || ''
    
    // Auto-detect if no locator_type provided but target is given
    if (!step.locator_type && targetVal) {
      if (targetVal.startsWith('/')) locType = 'xpath'
      else if (targetVal.startsWith('#') || targetVal.startsWith('.')) locType = 'css'
      else locType = 'css'
    }
    
    elementFormValue.value = {
      id: null,
      name: step.description || '未命名元素 (自动生成)', // Fallback to step description
      description: '',
      locator_type: locType,
      locator_value: targetVal
    }
  }
  
  showElementModal.value = true
}

const handleSaveElement = async () => {
  elementFormRef.value?.validate(async (errors) => {
    if (!errors && editingStepIndex.value !== null) {
      const stepIndex = editingStepIndex.value
      
      if (elementIsLibraryMode.value && elementFormValue.value.id) {
        // Save to backend library
        try {
          const data = {
             name: elementFormValue.value.name,
             description: elementFormValue.value.description,
             locator_type: elementFormValue.value.locator_type,
             locator_value: elementFormValue.value.locator_value,
             // The page_id cannot be changed from this view, grab from existing step
             page_id: formValue.value.steps[stepIndex].page_id
          }
          await api.put(`/elements/${elementFormValue.value.id}`, data)
          message.success('已同步更新项目元素库')
          showElementModal.value = false
          // Refresh elements to get new data in UI
          if (data.page_id) {
            await fetchElementsForPage(data.page_id)
          }
        } catch (e) {
          message.error('更新元素库失败')
        }
      } else {
        // Save locally to step (Custom Locator)
        formValue.value.steps[stepIndex].target = elementFormValue.value.locator_value
        formValue.value.steps[stepIndex].selector = elementFormValue.value.locator_value
        formValue.value.steps[stepIndex].locator_type = elementFormValue.value.locator_type
        
        // Use name as friendly description if no other description exists
        if (elementFormValue.value.name && (!formValue.value.steps[stepIndex].description || formValue.value.steps[stepIndex].description.includes('自动生成'))) {
          formValue.value.steps[stepIndex].description = elementFormValue.value.name
        }
        
        message.success('自定义定位配置已更新 (仅本次用例生效)')
        showElementModal.value = false
      }
    }
  })
}

const handleGenerateSteps = async () => {
  if (!aiPrompt.value.trim()) return
  aiLoading.value = true
  
  try {
    if (agentMode.value) {
      // Precision Mode: Real-time streaming from Agent
      const response = await fetch('/api/v1/agent/execute_stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          task: aiPrompt.value,
          model_id: selectedAIModel.value,
          headless: true,
          max_steps: 20,
          use_vision: false
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || '请求失败')
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('流读取器不可用')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const item = JSON.parse(line)
            if (item.type === 'step' && item.data) {
              const s = item.data
              // Convert Agent action to Platform step
              formValue.value.steps.push({
                action: s.action,
                target: s.target || '',
                selector: s.target || '',
                value: s.value || '',
                locator_chain: s.locator_chain || null,
                locator_type: s.locator_type || null,
                description: s.description || '',
                variable_name: s.variable_name || '',
                page_id: null,
                element_id: null,
                _custom_locator_mode: true
              })
            } else if (item.type === 'error') {
              message.error(item.message)
            }
          } catch (e) {
            console.error('Failed to parse agent stream line', e)
          }
        }
      }
      message.success('精度模式执行完成')
      showAIModal.value = false
      aiPrompt.value = ''
    } else {
      // Fast Mode: Normal generation
      const aiContext = await loadAiContext(selectedProjectId.value, selectedModuleId.value)
      const resp = await api.post('/ai/generate', { 
        prompt: aiPrompt.value,
        model_id: selectedAIModel.value,
        project_id: selectedProjectId.value,
        business_rules: aiContext.businessRules || undefined
      })
      
      const generatedSteps = resp.data.steps
      if (generatedSteps && generatedSteps.length > 0) {
        const parseDurationToMs = (raw: any): string => {
          if (raw === null || raw === undefined) return ''
          const text = String(raw).trim().toLowerCase()
          if (!text) return ''
          const m = text.match(/^(\d+(?:\.\d+)?)\s*(ms|s)?$/)
          if (!m) return String(raw).trim()
          const amount = Number(m[1])
          const unit = m[2]
          if (unit === 'ms') return String(Math.round(amount))
          if (unit === 's') return String(Math.round(amount * 1000))
          return String(Math.round(amount >= 100 ? amount : amount * 1000))
        }

        const isValidUrl = (val: string) => {
          try {
            const u = new URL(val)
            return u.protocol === 'http:' || u.protocol === 'https:'
          } catch {
            return false
          }
        }

        const mapAction = (action: string): { normalized: string; degraded: boolean } => {
          const a = (action || '').toLowerCase()
          if (a.includes('wait_for_selector') || a.includes('wait for selector') || a.includes('等待元素')) return { normalized: 'wait_for_selector', degraded: false }
          if (a.includes('assert_visible') || a.includes('visible') || a.includes('可见')) return { normalized: 'assert_visible', degraded: false }
          if (a.includes('assert') || a.includes('verify') || a.includes('check') || a.includes('断言') || a.includes('验证') || a.includes('检查')) return { normalized: 'assert_text', degraded: false }
          if (a.includes('hover') || a.includes('悬停')) return { normalized: 'hover', degraded: false }
          if (a.includes('select') || a.includes('选择')) return { normalized: 'select', degraded: false }
          if (a.includes('press') || a.includes('按键')) return { normalized: 'press', degraded: false }
          if (a.includes('click') || a.includes('点击')) return { normalized: 'click', degraded: false }
          if (a.includes('fill') || a.includes('type') || a.includes('input') || a.includes('输入') || a.includes('填写')) return { normalized: 'fill', degraded: false }
          if (a.includes('goto') || a.includes('visit') || a.includes('open') || a.includes('navigate') || a.includes('跳转') || a.includes('访问') || a.includes('打开')) return { normalized: 'goto', degraded: false }
          if (a.includes('wait') || a.includes('sleep') || a.includes('等待')) return { normalized: 'wait', degraded: false }
          if (a.includes('screenshot') || a.includes('截图')) return { normalized: 'screenshot', degraded: false }
          if (a.includes('get_text') || a.includes('text_content') || a.includes('提取文本')) return { normalized: 'get_text', degraded: false }
          if (a.includes('get_attribute') || a.includes('extract_attr') || a.includes('提取属性')) return { normalized: 'get_attribute', degraded: false }
          if (a.includes('set_variable') || a.includes('设置变量')) return { normalized: 'set_variable', degraded: false }
          return { normalized: 'click', degraded: true }
        }

        let degradedCount = 0
        const mappedSteps = generatedSteps.map((s: any) => {
          const mapped = mapAction(s.action)
          if (mapped.degraded) degradedCount += 1
          const action = mapped.normalized
          let val = String(s.value || '').trim()
          let tar = s.target || s.selector || ''
          
          if (action === 'goto' && !val && tar) {
            val = tar
            tar = ''
          }

          if (action === 'wait') {
            val = parseDurationToMs(s.wait_ms ?? val)
            if (!val) val = '1000'
          }
          if (action === 'goto' && val && !isValidUrl(val)) {
            message.warning(`检测到疑似无效 URL: ${val}，请编辑后再执行`)
          }
          
          return {
            action: action,
            target: String(tar || '').trim(),
            selector: String(tar || '').trim(),
            value: String(val || '').trim(),
            wait_ms: action === 'wait' ? (Number(val) || 1000) : (s.wait_ms ?? null),
            locator_chain: s.locator_chain || null,
            locator_type: s.locator_type || null,
            description: s.description || '',
            variable_name: s.variable_name || '',
            page_id: null,
            element_id: null
          }
        })

        const binding = bindGeneratedStepsToKnownElements(mappedSteps, aiContext.knownElements)
        const finalSteps = binding.steps.map((s: any) => ({
          ...s,
          _custom_locator_mode: !s.element_id
        }))
        formValue.value.steps = [...formValue.value.steps, ...finalSteps]
        
        if (degradedCount > 0) {
          message.warning(`有 ${degradedCount} 个步骤动作无法识别，已降级为 click，请检查后执行`)
        }
        if (binding.boundCount > 0) {
          message.info(`已自动绑定 ${binding.boundCount} 个步骤到已知页面元素`)
        }
        if (binding.unboundInteractiveCount > 0) {
          message.warning(`仍有 ${binding.unboundInteractiveCount} 个交互步骤未绑定到已知元素，建议确认页面元素库`)
        }
        message.success(`成功解析并添加 ${binding.steps.length} 个步骤`)
        showAIModal.value = false
        aiPrompt.value = ''
      } else {
        message.warning('未生成步骤，请尝试换种描述')
      }
    }
  } catch (error: any) {
    message.error(error.message || 'AI 解析异常')
  } finally {
    aiLoading.value = false
  }
}

onMounted(async () => {
  await fetchProjects()
  await fetchAIModels()
})
</script>

<style scoped>
.card-wrap {
  background: var(--color-card);
  border-radius: 8px;
  border: 1px solid var(--color-divider);
  overflow: hidden;
}

.custom-table :deep(.n-data-table-td) {
  padding: 6px 16px;
  font-size: 13px;
}

.custom-table :deep(.n-data-table-th) {
  padding: 8px 16px;
  background-color: #fafbfc;
  font-weight: 600;
  font-size: 13px;
}
</style>
