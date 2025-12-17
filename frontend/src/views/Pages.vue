<template>
  <div class="pages-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>页面管理</h1>
        <p>管理项目模块下的页面</p>
      </div>
      <n-space>
        <n-select
          v-model:value="selectedModuleId"
          :options="moduleOptions"
          placeholder="选择模块"
          style="width: 200px"
          @update:value="fetchPages"
        />
        <n-button type="primary" @click="showCreateModal = true" :disabled="!selectedModuleId">
          <template #icon>
            <span style="font-size: 18px;">➕</span>
          </template>
          创建页面
        </n-button>
      </n-space>
    </div>

    <!-- Pages Table -->
    <n-card :bordered="false" class="table-card">
      <n-data-table
        :columns="columns"
        :data="pages"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal" style="width: 600px">
      <n-card
        :title="editingId ? '编辑页面' : '创建页面'"
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
          <n-form-item label="页面名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="请输入页面名称" />
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="请输入描述（可选）"
              :autosize="{ minRows: 3, maxRows: 5 }"
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

interface Module {
  id: number
  name: string
}

const message = useMessage()
const loading = ref(false)
const pages = ref<Page[]>([])
const modules = ref<Module[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const selectedModuleId = ref<number | null>(null)
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
    message: '请输入页面名称',
    trigger: 'blur'
  }
}

const columns: DataTableColumns<Page> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
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
  { title: '创建人', key: 'creator_name', width: 120 },
  { title: '更新人', key: 'updater_name', width: 120 },
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
      fetchPages()
    }
  } catch (error) {
    message.error('获取模块列表失败')
  }
}

const fetchPages = async () => {
  if (!selectedModuleId.value) return
  loading.value = true
  try {
    const response = await api.get(`/pages/?module_id=${selectedModuleId.value}`)
    pages.value = response.data
  } catch (error) {
    message.error('获取页面列表失败')
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
          message.success('页面更新成功')
        } else {
          await api.post('/pages/', data)
          message.success('页面创建成功')
        }
        handleCloseModal()
        fetchPages()
      } catch (error) {
        message.error(editingId.value ? '更新页面失败' : '创建页面失败')
      }
    }
  })
}

const handleEdit = (row: Page) => {
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

const handleDelete = async (row: Page) => {
  try {
    await api.delete(`/pages/${row.id}`)
    message.success('页面删除成功')
    fetchPages()
  } catch (error) {
    message.error('删除页面失败')
  }
}

onMounted(() => {
  fetchModules()
})
</script>

<style scoped>
.pages-container {
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
