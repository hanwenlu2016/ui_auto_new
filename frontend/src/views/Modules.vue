<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1>模块管理</h1>
        <p>管理所属项目下的功能模块</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="过滤: 选择所属项目"
          style="width: 200px"
          @update:value="fetchModules"
          clearable
        />
        <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedProjectId">
          <template #icon>
            <span style="font-size: 16px;">➕</span>
          </template>
          创建模块
        </n-button>
      </div>
    </div>

    <!-- Search / Filter Area -->
    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s; margin-bottom: 20px; padding: 16px;">
      <n-form inline label-placement="left" :show-feedback="false" size="small" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
        <n-form-item label="模块名称">
          <n-input v-model:value="searchForm.name" placeholder="请输入名称" clearable style="width: 160px;" />
        </n-form-item>
        <n-form-item label="创建时间">
          <n-date-picker v-model:value="searchForm.dateRange" type="daterange" clearable style="width: 240px;" />
        </n-form-item>
        <n-form-item label="创建人">
          <n-input v-model:value="searchForm.creator" placeholder="创建人姓名" clearable style="width: 120px;" />
        </n-form-item>
        <div style="display: flex; gap: 12px; margin-left: auto;">
          <n-button @click="handleReset" secondary size="small">重置</n-button>
          <n-button type="primary" @click="handleSearch" size="small">搜索匹配</n-button>
        </div>
      </n-form>
    </div>

    <!-- Modules Table -->
    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.2s; padding: 0;">
      <n-data-table
        :columns="columns"
        :data="modules"
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
        :title="editingId ? '✏️ 编辑模块' : '➕ 创建模块'"
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
          <n-form-item label="模块名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="例如：登录模块、支付中心" />
          </n-form-item>
          <n-form-item label="描述说明" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="简述该模块的业务范围（可选）"
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
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NDatePicker } from 'naive-ui'
import api from '@/api'

interface Module {
  id: number
  name: string
  description: string
  project_id: number
  created_at: string
  updated_at: string
  creator_name: string
  updater_name: string
}

const message = useMessage()
const loading = ref(false)
const modules = ref<Module[]>([])
const projects = ref<any[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(null)
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

const searchForm = ref({
  name: '',
  creator: '',
  updater: '',
  dateRange: null as [number, number] | null
})

const formValue = ref({
  name: '',
  description: ''
})

const rules = {
  name: { required: true, message: '请输入模块名称', trigger: 'blur' }
}

const columns: DataTableColumns<Module> = [
  { title: '模块名称', key: 'name', minWidth: 200, fixed: 'left' },
  { title: '业务描述', key: 'description' },
  { 
    title: '创建时间', 
    key: 'created_at',
    width: 170,
    render: (row) => row.created_at ? new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) : '-'
  },
  { title: '维护人', key: 'updater_name', width: 120, render: (row) => row.updater_name || row.creator_name || '-' },
  {
    title: '操作',
    key: 'actions',
    width: 120,
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
      fetchModules()
    }
  } catch (error) {
    message.error('获取项目列表失败')
  }
}

const fetchModules = async () => {
  if (!selectedProjectId.value) return
  loading.value = true
  try {
    let url = `/modules/?project_id=${selectedProjectId.value}`
    if (searchForm.value.name) url += `&name=${searchForm.value.name}`
    if (searchForm.value.creator) url += `&creator=${searchForm.value.creator}`
    if (searchForm.value.updater) url += `&updater=${searchForm.value.updater}`
    if (searchForm.value.dateRange) {
      url += `&created_after=${new Date(searchForm.value.dateRange[0]).toISOString()}`
      url += `&created_before=${new Date(searchForm.value.dateRange[1]).toISOString()}`
    }
    const response = await api.get(url)
    modules.value = response.data
  } catch (error) {
    message.error('获取列表数据失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => fetchModules()

const handleReset = () => {
  searchForm.value = { name: '', creator: '', updater: '', dateRange: null }
  fetchModules()
}

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedProjectId.value) {
      try {
        const data = { ...formValue.value, project_id: selectedProjectId.value }
        if (editingId.value) {
          await api.put(`/modules/${editingId.value}`, data)
          message.success('模块修改成功')
        } else {
          await api.post('/modules/', data)
          message.success('新模块已创建')
        }
        handleCloseModal()
        fetchModules()
      } catch (error) {
        message.error(editingId.value ? '保存失败' : '创建失败')
      }
    }
  })
}

const handleEdit = (row: Module) => {
  editingId.value = row.id
  formValue.value = { name: row.name, description: row.description || '' }
  showCreateModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  formValue.value = { name: '', description: '' }
  editingId.value = null
}

const handleDelete = async (row: Module) => {
  try {
    await api.delete(`/modules/${row.id}`)
    message.success('模块已删除')
    fetchModules()
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
