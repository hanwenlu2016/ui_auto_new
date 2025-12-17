<template>
  <div class="test-suites-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>测试套件</h1>
        <p>管理和执行测试套件</p>
      </div>
      <n-space>
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="选择项目"
          style="width: 200px"
          @update:value="fetchTestSuites"
        />
        <n-button type="primary" @click="handleOpenCreate" :disabled="!selectedProjectId">
          <template #icon>
            <span style="font-size: 18px;">➕</span>
          </template>
          创建套件
        </n-button>
      </n-space>
    </div>

    <!-- Test Suites Table -->
    <n-card :bordered="false" class="table-card">
      <n-data-table
        :columns="columns"
        :data="testSuites"
        :loading="loading"
        :pagination="pagination"
      />
    </n-card>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal" style="width: 800px">
      <n-card
        :title="editingId ? '编辑套件' : '创建套件'"
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
          <n-form-item label="套件名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="请输入套件名称" />
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="请输入描述（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
          
          <n-form-item label="关联用例" path="test_case_ids">
            <n-transfer
              v-model:value="formValue.test_case_ids"
              :options="testCaseOptions"
              source-title="可用用例"
              target-title="已选用例"
              filterable
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
import { NButton, NSpace, useMessage, type DataTableColumns, type FormInst, NCard, NDataTable, NModal, NForm, NFormItem, NInput, NSelect, NTransfer } from 'naive-ui'
import api from '@/api'

interface TestSuite {
  id: number
  name: string
  description: string
  project_id: number
  test_cases: any[]
  created_at: string
  updated_at: string
  creator_name: string
  updater_name: string
}

interface Project {
  id: number
  name: string
}

const message = useMessage()
const loading = ref(false)
const testSuites = ref<TestSuite[]>([])
const projects = ref<Project[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(null)
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)
const testCaseOptions = ref<{ label: string; value: number }[]>([])

const formValue = ref({
  name: '',
  description: '',
  test_case_ids: [] as number[]
})

const rules = {
  name: {
    required: true,
    message: '请输入套件名称',
    trigger: 'blur'
  }
}

const columns: DataTableColumns<TestSuite> = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name' },
  { title: '描述', key: 'description' },
  { 
    title: '用例数', 
    key: 'test_cases',
    render(row) {
      return row.test_cases?.length || 0
    }
  },
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
      fetchTestSuites()
    }
  } catch (error) {
    message.error('获取项目列表失败')
  }
}

const fetchTestSuites = async () => {
  if (!selectedProjectId.value) return
  loading.value = true
  try {
    const response = await api.get(`/suites/?project_id=${selectedProjectId.value}`)
    testSuites.value = response.data
  } catch (error) {
    message.error('获取测试套件列表失败')
  } finally {
    loading.value = false
  }
}

const fetchTestCases = async () => {
  if (!selectedProjectId.value) return
  try {
    // Fetch all modules for the project first
    const modulesRes = await api.get(`/modules/?project_id=${selectedProjectId.value}`)
    const modules = modulesRes.data
    
    let allCases: any[] = []
    for (const module of modules) {
      const casesRes = await api.get(`/cases/?module_id=${module.id}`)
      allCases = [...allCases, ...casesRes.data]
    }
    
    testCaseOptions.value = allCases.map(c => ({
      label: c.name,
      value: c.id
    }))
  } catch (error) {
    message.error('获取测试用例失败')
  }
}

const handleOpenCreate = async () => {
  await fetchTestCases()
  showCreateModal.value = true
}

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors && selectedProjectId.value) {
      try {
        const data = { ...formValue.value, project_id: selectedProjectId.value }
        if (editingId.value) {
          await api.put(`/suites/${editingId.value}`, data)
          message.success('套件更新成功')
        } else {
          await api.post('/suites/', data)
          message.success('套件创建成功')
        }
        handleCloseModal()
        fetchTestSuites()
      } catch (error) {
        message.error(editingId.value ? '更新套件失败' : '创建套件失败')
      }
    }
  })
}

const handleEdit = async (row: TestSuite) => {
  await fetchTestCases()
  editingId.value = row.id
  formValue.value = {
    name: row.name,
    description: row.description,
    test_case_ids: row.test_cases?.map((c: any) => c.id) || []
  }
  showCreateModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  formValue.value = { name: '', description: '', test_case_ids: [] }
  editingId.value = null
}

const handleDelete = async (row: TestSuite) => {
  try {
    await api.delete(`/suites/${row.id}`)
    message.success('套件删除成功')
    fetchTestSuites()
  } catch (error) {
    message.error('删除套件失败')
  }
}

const handleRun = async (row: TestSuite) => {
  try {
    message.loading('正在启动测试套件...')
    const response = await api.post(`/execution/suites/${row.id}/run`)
    if (response.data.task_id) {
      message.success('测试套件已启动，请前往测试报告页面查看结果')
    } else {
      message.error(`启动测试套件失败: ${response.data.message || '未知错误'}`)
    }
  } catch (error) {
    message.error('执行测试套件失败')
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.test-suites-container {
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
