<template>
  <div class="page-elements-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>页面元素</h1>
        <p>管理页面元素定位信息</p>
      </div>
      <n-space>
        <n-select
          v-model:value="selectedModuleId"
          :options="moduleOptions"
          placeholder="选择模块"
          style="width: 200px"
        />
        <n-select
          v-model:value="selectedPageId"
          :options="pageOptions"
          placeholder="选择页面"
          style="width: 200px"
          :disabled="!selectedModuleId"
        />
        <n-button type="primary" @click="handleOpenCreate" :disabled="!selectedPageId">
          <template #icon>
            <span style="font-size: 18px;">➕</span>
          </template>
          创建元素
        </n-button>
      </n-space>
    </div>

    <!-- Elements Table -->
    <n-card :bordered="false" class="table-card">
      <n-data-table
        :columns="columns"
        :data="elements"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal">
      <n-card
        style="width: 600px"
        :title="editingId ? '编辑元素' : '创建元素'"
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
          <n-form-item label="元素名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="请输入元素名称" />
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="请输入描述（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
          <n-grid :cols="2" :x-gap="24">
            <n-form-item-grid-item label="定位方式" path="locator_type">
              <n-select
                v-model:value="formValue.locator_type"
                :options="locatorOptions"
                placeholder="选择定位方式"
              />
            </n-form-item-grid-item>
            <n-form-item-grid-item label="定位值" path="locator_value">
              <n-input v-model:value="formValue.locator_value" placeholder="例如: //div[@id='app']" />
            </n-form-item-grid-item>
          </n-grid>
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
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NGrid, NFormItemGridItem, NTag } from 'naive-ui'
import api from '@/api'

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

interface Module {
  id: number
  name: string
}

interface Page {
  id: number
  name: string
}

const message = useMessage()
const loading = ref(false)
const elements = ref<PageElement[]>([])
const modules = ref<Module[]>([])
const pages = ref<Page[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const pageOptions = ref<{ label: string; value: number }[]>([])
const selectedModuleId = ref<number | null>(null)
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
  name: {
    required: true,
    message: '请输入元素名称',
    trigger: 'blur'
  },
  locator_type: {
    required: true,
    message: '请选择定位方式',
    trigger: 'change'
  },
  locator_value: {
    required: true,
    message: '请输入定位值',
    trigger: 'blur'
  }
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
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  { 
    title: '定位方式', 
    key: 'locator_type',
    width: 120,
    render(row) {
      return h(NTag, { type: 'info', size: 'small' }, { default: () => row.locator_type })
    }
  },
  { title: '定位值', key: 'locator_value', ellipsis: true },
  { title: '描述', key: 'description', ellipsis: true },
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
    selectedPageId.value = null
    return
  }
  try {
    const response = await api.get(`/pages/?module_id=${selectedModuleId.value}`)
    pages.value = response.data
    pageOptions.value = pages.value.map(p => ({
      label: p.name,
      value: p.id
    }))
    if (pages.value.length > 0) {
      selectedPageId.value = pages.value[0].id
    } else {
      selectedPageId.value = null
    }
  } catch (error) {
    message.error('获取页面列表失败')
  }
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
    message.error('获取元素列表失败')
  } finally {
    loading.value = false
  }
}

watch(selectedModuleId, () => {
  fetchPages()
})

watch(selectedPageId, () => {
  fetchElements()
})

const handleOpenCreate = () => {
  showCreateModal.value = true
}

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedPageId.value) {
      try {
        const data = { ...formValue.value, page_id: selectedPageId.value }
        if (editingId.value) {
          await api.put(`/elements/${editingId.value}`, data)
          message.success('元素更新成功')
        } else {
          await api.post('/elements/', data)
          message.success('元素创建成功')
        }
        handleCloseModal()
        fetchElements()
      } catch (error) {
        message.error(editingId.value ? '更新元素失败' : '创建元素失败')
      }
    }
  })
}

const handleEdit = (row: PageElement) => {
  editingId.value = row.id
  formValue.value = {
    name: row.name,
    description: row.description,
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
    message.success('元素删除成功')
    fetchElements()
  } catch (error) {
    message.error('删除元素失败')
  }
}

onMounted(() => {
  fetchModules()
})
</script>

<style scoped>
.page-elements-container {
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
