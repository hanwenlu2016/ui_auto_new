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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch } from 'vue'
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
}

const message = useMessage()
const loading = ref(false)
const elements = ref<PageElement[]>([])
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
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

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
    width: 160,
    fixed: 'right' as const,
    render(row) {
      return h(NSpace, { align: 'center', wrap: false, size: 8 }, {
        default: () => [
          h(NButton, { size: 'small', quaternary: true, type: 'primary', onClick: () => handleEdit(row) }, { default: () => '编辑' }),
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
  } catch (error) {
    message.error('获取列表数据失败')
  } finally {
    loading.value = false
  }
}

watch(selectedModuleId, (val) => {
  appStore.setModuleId(val)
  fetchPages()
})
watch(selectedPageId, () => fetchElements())

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
</style>
