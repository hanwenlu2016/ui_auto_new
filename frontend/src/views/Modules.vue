<template>
  <div class="modules-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>模块管理</h1>
        <p>管理项目下的功能模块</p>
      </div>
      <n-space>
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="选择项目"
          style="width: 200px"
          @update:value="fetchModules"
        />
        <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedProjectId">
          <template #icon>
            <span style="font-size: 18px;">➕</span>
          </template>
          创建模块
        </n-button>
      </n-space>
    </div>

    <!-- Modules Table -->
    <n-card :bordered="false" class="table-card">
      <n-data-table
        :columns="columns"
        :data="modules"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal">
      <n-card
        style="width: 600px"
        :title="editingId ? '编辑模块' : '创建模块'"
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
          <n-form-item label="模块名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="请输入模块名称" />
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="请输入描述（可选）"
              :autosize="{ minRows: 3, maxRows: 6 }"
            />
          </n-form-item>
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
import { ref, onMounted, h } from 'vue'
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect } from 'naive-ui'
import api from '@/api'

interface Module {
  id: number
  name: string
  description: string
  project_id: number
}

interface Project {
  id: number
  name: string
}

const message = useMessage()
const loading = ref(false)
const modules = ref<Module[]>([])
const projects = ref<Project[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(null)
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

const formValue = ref({
  name: '',
  description: ''
})

const rules = {
  name: {
    required: true,
    message: '请输入模块名称',
    trigger: 'blur'
  }
}

const columns: DataTableColumns<Module> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  { title: '描述', key: 'description' },
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

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
    projectOptions.value = projects.value.map(p => ({
      label: p.name,
      value: p.id
    }))
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
    const response = await api.get(`/modules/?project_id=${selectedProjectId.value}`)
    modules.value = response.data
  } catch (error) {
    message.error('获取模块列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedProjectId.value) {
      try {
        const data = { ...formValue.value, project_id: selectedProjectId.value }
        if (editingId.value) {
          await api.put(`/modules/${editingId.value}`, data)
          message.success('模块更新成功')
        } else {
          await api.post('/modules/', data)
          message.success('模块创建成功')
        }
        handleCloseModal()
        fetchModules()
      } catch (error) {
        message.error(editingId.value ? '更新模块失败' : '创建模块失败')
      }
    }
  })
}

const handleEdit = (row: Module) => {
  editingId.value = row.id
  formValue.value = {
    name: row.name,
    description: row.description
  }
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
    message.success('模块删除成功')
    fetchModules()
  } catch (error) {
    message.error('删除模块失败')
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.modules-container {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 16px 24px;
  border-radius: 4px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
}

.header-text h1 {
  font-size: 20px;
  font-weight: 500;
  color: #1f2225;
  margin: 0 0 4px 0;
}

.header-text p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.table-card {
  border-radius: 4px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
}

.modal-card {
  border-radius: 4px;
}

.modal-card :deep(.n-card-header) {
  padding: 16px 24px;
  border-bottom: 1px solid #e8eaec;
  font-size: 16px;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
}
</style>
