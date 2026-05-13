<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1>页面元素</h1>
        <p>管理系统中所有用于 UI 测试的元素定位信息</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="项目"
          style="width: 140px"
          @update:value="handleProjectChange"
        />
        <n-select
          v-model:value="selectedModuleId"
          :options="moduleOptions"
          placeholder="模块"
          style="width: 140px"
          @update:value="handleModuleChange"
          clearable
        />
        <n-select
          v-model:value="selectedPageId"
          :options="pageOptions"
          placeholder="过滤: 选择目标页面"
          style="width: 160px"
          :disabled="!selectedModuleId"
          clearable
        />
        <n-button type="primary" @click="handleOpenCreate" :disabled="!selectedPageId">
          <template #icon>
            <span style="font-size: 16px;">➕</span>
          </template>
          创建元素
        </n-button>
      </div>
    </div>

    <!-- Elements Table -->
    <div
      class="card-wrap shadow-sm animate-fade-up review-card"
      style="animation-delay: 0.05s; margin-bottom: 16px;"
      v-if="healSuggestions.length > 0 || healLoading"
    >
      <div class="review-header">
        <div>
          <div class="review-title">待确认的选择器升级</div>
          <div class="review-subtitle">来自运行期自愈的候选选择器，可人工确认后提升为正式主选择器</div>
        </div>
        <n-tag type="warning" size="small" :bordered="false">
          {{ healSuggestions.length }} 条待处理
        </n-tag>
      </div>
      <n-data-table
        :columns="healColumns"
        :data="healSuggestions"
        :loading="healLoading"
        size="small"
        :bordered="false"
        class="custom-table"
      />
    </div>

    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s; padding: 0;">
      <n-data-table
        :columns="columns"
        :data="elements"
        :loading="loading"
        :pagination="pagination"
        size="small"
        :bordered="false"
        class="custom-table"
      />
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal">
      <n-card
        style="width: 650px; max-width: 90vw"
        :title="editingId ? '✏️ 编辑元素' : '➕ 创建元素'"
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
          <n-form-item label="元素名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="例如：登录按钮、用户名输入框" />
          </n-form-item>
          <n-form-item label="元素描述" path="description">
            <n-input
              v-model:value="formValue.description"
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
                  v-model:value="formValue.locator_type"
                  :options="locatorOptions"
                  placeholder="选择方式"
                />
              </n-form-item>
              <n-form-item label="定位特征值" path="locator_value" style="margin-bottom: 0;">
                <n-input v-model:value="formValue.locator_value" placeholder="例如: #login-btn 或 //*[@id='app']" />
              </n-form-item>
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

    <n-modal v-model:show="showHistoryModal">
      <n-card
        style="width: 820px; max-width: 96vw"
        title="选择器学习记录"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <template v-if="selectedElement">
          <div class="history-header">
            <div>
              <div class="history-element-name">{{ selectedElement.name }}</div>
              <div class="history-element-desc">{{ selectedElement.description || '暂无元素描述' }}</div>
            </div>
            <n-tag type="info" :bordered="false">{{ selectedElement.locator_type.toUpperCase() }}</n-tag>
          </div>

          <div class="history-section">
            <div class="history-section-title">当前主选择器</div>
            <div class="selector-card current">{{ selectedElement.locator_value }}</div>
          </div>

          <div class="history-grid">
            <div class="history-section">
              <div class="history-section-title">已学习的备用选择器</div>
              <div v-if="learnedSelectors.length > 0" class="selector-list">
                <div v-for="selector in learnedSelectors" :key="selector" class="selector-card">
                  {{ selector }}
                </div>
              </div>
              <div v-else class="empty-hint">暂无学习到的备用选择器</div>
            </div>

            <div class="history-section">
              <div class="history-section-title">历史主选择器</div>
              <div v-if="previousPrimarySelectors.length > 0" class="selector-list">
                <div v-for="selector in previousPrimarySelectors" :key="selector" class="selector-card rollback">
                  <span class="selector-text">{{ selector }}</span>
                  <n-button size="tiny" type="primary" secondary @click="handleRollbackSelector(selector)">
                    回滚到此
                  </n-button>
                </div>
              </div>
              <div v-else class="empty-hint">暂无可回滚的历史主选择器</div>
            </div>
          </div>

          <div class="history-section">
            <div class="history-section-title">学习备注</div>
            <div v-if="learningNotes.length > 0" class="notes-list">
              <div v-for="note in learningNotes" :key="note" class="note-item">{{ note }}</div>
            </div>
            <div v-else class="empty-hint">暂无学习备注</div>
          </div>
        </template>

        <template #footer>
          <div style="display: flex; justify-content: flex-end;">
            <n-button @click="showHistoryModal = false">关闭</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch, computed } from 'vue'
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NTag } from 'naive-ui'
import api from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

interface PageElement {
  id: number
  name: string
  description: string
  locator_type: string
  locator_value: string
  page_id: number
  created_at: string
  updated_at: string
  creator_name: string
  updater_name: string
  metadata_json?: Record<string, any> | null
}

interface HealSuggestion {
  id: number
  element_id: number | null
  element_name: string | null
  page_id: number | null
  page_name: string | null
  original_selector: string
  healed_selector: string | null
  candidate_selector: string | null
  confidence: number
  change_summary: string | null
  explanation: string | null
  status: string
  created_at: string | null
}

const message = useMessage()
const loading = ref(false)
const healLoading = ref(false)
const elements = ref<PageElement[]>([])
const healSuggestions = ref<HealSuggestion[]>([])
const projects = ref<any[]>([])
const modules = ref<any[]>([])
const pages = ref<any[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const pageOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(appStore.selectedProjectId)
const selectedModuleId = ref<number | null>(appStore.selectedModuleId)
const selectedPageId = ref<number | null>(null)
const showCreateModal = ref(false)
const showHistoryModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)
const selectedElement = ref<PageElement | null>(null)

const formValue = ref({
  name: '',
  description: '',
  locator_type: 'xpath',
  locator_value: ''
})

const rules = {
  name: { required: true, message: '请输入元素名称', trigger: 'blur' },
  locator_type: { required: true, message: '请选择定位方式', trigger: 'change' },
  locator_value: { required: true, message: '请输入定位特征值', trigger: 'blur' }
}

const locatorOptions = [
  { label: 'XPath', value: 'xpath' },
  { label: 'CSS Selector', value: 'css' },
  { label: 'ID', value: 'id' },
  { label: 'Name', value: 'name' },
  { label: 'Class Name', value: 'class_name' },
  { label: 'Link Text', value: 'link_text' }
]

const learnedSelectors = computed(() => selectedElement.value ? getLearnedSelectors(selectedElement.value) : [])
const previousPrimarySelectors = computed(() => selectedElement.value ? getPreviousPrimarySelectors(selectedElement.value) : [])
const learningNotes = computed(() => {
  const notes = selectedElement.value?.metadata_json?.learning_notes
  return Array.isArray(notes) ? notes : []
})

const columns: DataTableColumns<PageElement> = [
  { title: '元素名称', key: 'name', minWidth: 150 },
  { 
    title: '定位方式', 
    key: 'locator_type',
    width: 120,
    render(row) {
      return h(NTag, { type: 'info', size: 'small', bordered: false, style: 'font-weight: 500;' }, { default: () => row.locator_type.toUpperCase() })
    }
  },
  {
    title: '学习状态',
    key: 'learning_state',
    width: 130,
    render(row) {
      const learnedCount = getLearnedSelectors(row).length
      const historyCount = getPreviousPrimarySelectors(row).length
      if (learnedCount === 0 && historyCount === 0) {
        return h(NTag, { size: 'small', bordered: false }, { default: () => '未学习' })
      }
      return h(NTag, { type: 'success', size: 'small', bordered: false }, {
        default: () => `已学习 ${learnedCount + historyCount}`
      })
    }
  },
  { title: '定位特征值', key: 'locator_value', ellipsis: true },
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
    width: 230,
    fixed: 'right' as const,
    render(row) {
      return h(NSpace, { align: 'center', wrap: false, size: 8 }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, onClick: () => handleOpenHistory(row) }, { default: () => '学习记录' }),
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
          h(NButton, { size: 'small', quaternary: true, type: 'error', onClick: () => handleDelete(row) }, { default: () => '删除' })
        ]
      })
    }
  }
]

const healColumns: DataTableColumns<HealSuggestion> = [
  {
    title: '元素 / 页面',
    key: 'element_name',
    minWidth: 180,
    render(row) {
      return h('div', { class: 'heal-target' }, [
        h('div', { class: 'heal-target-name' }, row.element_name || '未知元素'),
        h('div', { class: 'heal-target-page' }, row.page_name || '未知页面')
      ])
    }
  },
  {
    title: '当前主选择器',
    key: 'original_selector',
    minWidth: 220,
    ellipsis: true
  },
  {
    title: '建议升级选择器',
    key: 'candidate_selector',
    minWidth: 260,
    ellipsis: true,
    render(row) {
      return h('div', { class: 'heal-suggestion-cell' }, [
        h('div', { class: 'heal-selector-primary' }, row.candidate_selector || '-'),
        row.change_summary ? h('div', { class: 'heal-selector-note' }, row.change_summary) : null
      ])
    }
  },
  {
    title: '置信度',
    key: 'confidence',
    width: 90,
    render(row) {
      return `${((row.confidence || 0) * 100).toFixed(0)}%`
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    fixed: 'right' as const,
    render(row) {
      return h(NSpace, { align: 'center', wrap: false, size: 8 }, {
        default: () => [
          h(NButton, {
            size: 'small',
            type: 'primary',
            secondary: true,
            disabled: !row.candidate_selector,
            onClick: () => handlePromoteSuggestion(row)
          }, { default: () => '提升为主' }),
          h(NButton, {
            size: 'small',
            quaternary: true,
            type: 'error',
            onClick: () => handleRejectSuggestion(row)
          }, { default: () => '驳回' })
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
    
    // Check if current module belongs here
    if (moduleOptions.value.length > 0) {
      if (!selectedModuleId.value || !moduleOptions.value.find(m => m.value === selectedModuleId.value)) {
        selectedModuleId.value = moduleOptions.value[0].value
        appStore.setModuleId(selectedModuleId.value)
      }
    } else {
      selectedModuleId.value = null
      appStore.setModuleId(null)
    }
    fetchPages()
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

const handleModuleChange = (val: number | null) => {
  selectedModuleId.value = val
  appStore.setModuleId(val)
  fetchPages()
}

const fetchPages = async () => {
  if (!selectedModuleId.value) {
    pageOptions.value = []
    selectedPageId.value = null
    return
  }
  try {
    const response = await api.get(`/pages/?module_id=${selectedModuleId.value}`)
    pages.value = response.data
    pageOptions.value = pages.value.map(p => ({ label: p.name, value: p.id }))
    if (pages.value.length > 0) {
      selectedPageId.value = pages.value[0].id
    } else {
      selectedPageId.value = null
    }
  } catch (error) {}
}

const fetchElements = async () => {
  if (!selectedPageId.value) {
    elements.value = []
    return
  }
  loading.value = true
  try {
    const response = await api.get(`/elements/?page_id=${selectedPageId.value}`)
    elements.value = response.data
    if (selectedElement.value) {
      const latest = elements.value.find((item) => item.id === selectedElement.value?.id)
      if (latest) {
        selectedElement.value = latest
      }
    }
  } catch (error) {
    message.error('获取列表数据失败')
  } finally {
    loading.value = false
  }
}

const getLearnedSelectors = (row: PageElement): string[] => {
  const metadata = row.metadata_json || {}
  const locatorChain = metadata.ai_recommended_locator_chain || {}
  const values = [
    ...(Array.isArray(metadata.human_verified_selectors) ? metadata.human_verified_selectors : []),
    metadata.last_healed_selector,
    locatorChain.primary,
    locatorChain.fallback_1,
    locatorChain.fallback_2,
    locatorChain.fallback_3,
    ...(Array.isArray(metadata.healing_selectors) ? metadata.healing_selectors : [])
  ]
  const seen = new Set<string>()
  const result: string[] = []
  for (const raw of values) {
    const value = String(raw || '').trim()
    if (!value || value === row.locator_value || seen.has(value)) continue
    seen.add(value)
    result.push(value)
  }
  return result
}

const getPreviousPrimarySelectors = (row: PageElement): string[] => {
  const values = Array.isArray(row.metadata_json?.previous_primary_selectors)
    ? row.metadata_json?.previous_primary_selectors
    : []
  const seen = new Set<string>()
  const result: string[] = []
  for (const raw of values) {
    const value = String(raw || '').trim()
    if (!value || value === row.locator_value || seen.has(value)) continue
    seen.add(value)
    result.push(value)
  }
  return result
}

const fetchHealSuggestions = async () => {
  if (!selectedProjectId.value) {
    healSuggestions.value = []
    return
  }

  healLoading.value = true
  try {
    const params = new URLSearchParams({
      project_id: String(selectedProjectId.value),
      status: 'auto_healed',
      limit: '30'
    })
    if (selectedPageId.value) {
      params.set('page_id', String(selectedPageId.value))
    }
    const response = await api.get(`/ai/heal-logs?${params.toString()}`)
    healSuggestions.value = (response.data || []).filter((item: HealSuggestion) => Boolean(item.candidate_selector))
  } catch (error) {
    message.error('获取待确认升级列表失败')
  } finally {
    healLoading.value = false
  }
}

watch(selectedModuleId, (val) => {
  appStore.setModuleId(val)
  fetchPages()
})
watch(selectedPageId, () => {
  fetchElements()
  fetchHealSuggestions()
})

const handleOpenCreate = () => showCreateModal.value = true

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedPageId.value) {
      try {
        const data = { ...formValue.value, page_id: selectedPageId.value }
        if (editingId.value) {
          await api.put(`/elements/${editingId.value}`, data)
          message.success('元素信息修改成功')
        } else {
          await api.post('/elements/', data)
          message.success('新元素已创建')
        }
        handleCloseModal()
        fetchElements()
      } catch (error) {
        message.error(editingId.value ? '保存失败' : '创建失败')
      }
    }
  })
}

const handleEdit = (row: PageElement) => {
  editingId.value = row.id
  formValue.value = {
    name: row.name,
    description: row.description || '',
    locator_type: row.locator_type,
    locator_value: row.locator_value
  }
  showCreateModal.value = true
}

const handleOpenHistory = (row: PageElement) => {
  selectedElement.value = row
  showHistoryModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  formValue.value = { name: '', description: '', locator_type: 'xpath', locator_value: '' }
  editingId.value = null
}

const handleDelete = async (row: PageElement) => {
  try {
    await api.delete(`/elements/${row.id}`)
    message.success('元素已删除')
    fetchElements()
  } catch (error) {}
}

const handleRollbackSelector = async (selector: string) => {
  if (!selectedElement.value) return
  try {
    const response = await api.post(`/elements/${selectedElement.value.id}/rollback-selector`, { selector })
    message.success('已回滚主选择器')
    selectedElement.value = response.data
    await fetchElements()
    await fetchHealSuggestions()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '回滚失败')
  }
}

const handlePromoteSuggestion = async (row: HealSuggestion) => {
  try {
    const response = await api.post(`/ai/heal-logs/${row.id}/promote`)
    message.success(response.data.message || '已提升为主选择器')
    await fetchHealSuggestions()
    if (selectedPageId.value && row.page_id === selectedPageId.value) {
      await fetchElements()
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提升失败')
  }
}

const handleRejectSuggestion = async (row: HealSuggestion) => {
  try {
    const response = await api.post(`/ai/heal-logs/${row.id}/reject`)
    message.success(response.data.message || '已驳回')
    await fetchHealSuggestions()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '驳回失败')
  }
}

onMounted(() => fetchProjects())
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

.review-card {
  padding: 0;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 16px 18px 12px 18px;
  border-bottom: 1px solid var(--color-divider);
  background: linear-gradient(135deg, #fff8e8 0%, #fffdf6 100%);
}

.review-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-1);
}

.review-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--color-text-3);
}

.heal-target-name {
  font-weight: 600;
  color: var(--color-text-1);
}

.heal-target-page {
  margin-top: 2px;
  font-size: 12px;
  color: var(--color-text-3);
}

.heal-suggestion-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.heal-selector-primary {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--color-text-1);
}

.heal-selector-note {
  font-size: 12px;
  color: var(--color-text-3);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 18px;
}

.history-element-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-1);
}

.history-element-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--color-text-3);
}

.history-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.history-section {
  margin-top: 16px;
}

.history-section-title {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-2);
}

.selector-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selector-card {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-divider);
  background: #fafbfc;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-1);
  word-break: break-all;
}

.selector-card.current {
  background: #eef5ff;
  border-color: rgba(79, 129, 255, 0.25);
}

.selector-card.rollback {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.selector-text {
  flex: 1;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.note-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid var(--color-divider);
  font-size: 12px;
  color: var(--color-text-2);
  line-height: 1.5;
}

.empty-hint {
  padding: 18px;
  border: 1px dashed var(--color-divider);
  border-radius: 10px;
  font-size: 12px;
  color: var(--color-text-3);
  background: #fcfcfd;
}
</style>
