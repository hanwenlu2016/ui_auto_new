<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1>页面管理</h1>
        <p>管理所属模块下的各个系统页面</p>
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
          @update:value="fetchPages"
          clearable
        />
        <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedModuleId">
          <template #icon>
            <span style="font-size: 16px;">➕</span>
          </template>
          创建页面
        </n-button>
      </div>
    </div>

    <!-- Pages Table -->
    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s; padding: 0;">
      <n-data-table
        :columns="columns"
        :data="pages"
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
        style="width: 500px; max-width: 90vw"
        :title="editingId ? '✏️ 编辑页面' : '➕ 创建页面'"
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
          <n-form-item label="页面名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="例如：用户管理页、订单详情" />
          </n-form-item>
          <n-form-item label="页面描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="添加相关人员或业务说明..."
              :autosize="{ minRows: 3, maxRows: 5 }"
            />
          </n-form-item>
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
import { ref, onMounted, h } from 'vue'
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect } from 'naive-ui'
import api from '@/api'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()

interface Page {
  id: number
  name: string
  description: string
  module_id: number
  created_at: string
  updated_at: string
  creator_name: string
  updater_name: string
}

const message = useMessage()
const loading = ref(false)
const pages = ref<Page[]>([])
const projects = ref<any[]>([])
const modules = ref<any[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(appStore.selectedProjectId)
const selectedModuleId = ref<number | null>(appStore.selectedModuleId)
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

const formValue = ref({
  name: '',
  description: ''
})

const rules = {
  name: { required: true, message: '请输入页面名称', trigger: 'blur' }
}

const columns: DataTableColumns<Page> = [
  { title: '页面名称', key: 'name', minWidth: 150 },
  { title: '页面描述', key: 'description' },
  { 
    title: '创建时间', 
    key: 'created_at',
    width: 170,
    render: (row) => row.created_at ? new Date(row.created_at).toLocaleString() : '-'
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

const fetchPages = async () => {
  if (!selectedModuleId.value) return
  loading.value = true
  try {
    const response = await api.get(`/pages/?module_id=${selectedModuleId.value}`)
    pages.value = response.data
  } catch (error) {
    message.error('获取列表数据失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedModuleId.value) {
      try {
        const data = { ...formValue.value, module_id: selectedModuleId.value }
        if (editingId.value) {
          await api.put(`/pages/${editingId.value}`, data)
          message.success('页面信息修改成功')
        } else {
          await api.post('/pages/', data)
          message.success('新页面已创建')
        }
        handleCloseModal()
        fetchPages()
      } catch (error) {
        message.error(editingId.value ? '保存失败' : '创建失败')
      }
    }
  })
}

const handleEdit = (row: Page) => {
  editingId.value = row.id
  formValue.value = { name: row.name, description: row.description || '' }
  showCreateModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  formValue.value = { name: '', description: '' }
  editingId.value = null
}

const handleDelete = async (row: Page) => {
  try {
    await api.delete(`/pages/${row.id}`)
    message.success('页面已删除')
    fetchPages()
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
