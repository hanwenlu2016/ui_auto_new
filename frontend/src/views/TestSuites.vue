<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center;">
      <div>
        <h1>测试套件</h1>
        <p>组装并执行批量的自动化测试用例</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <n-select
          v-model:value="selectedProjectId"
          :options="projectOptions"
          placeholder="过滤: 选择项目"
          style="width: 200px"
          @update:value="fetchTestSuites"
          clearable
        />
        <n-button type="primary" @click="handleOpenCreate" :disabled="!selectedProjectId">
          <template #icon>
            <span style="font-size: 16px;">➕</span>
          </template>
          创建套件
        </n-button>
      </div>
    </div>

    <!-- Test Suites Table -->
    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s">
      <n-data-table
        :columns="columns"
        :data="testSuites"
        :loading="loading"
        :pagination="pagination"
      />
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal">
      <n-card
        style="width: 700px; max-width: 90vw"
        :title="editingId ? '✏️ 编辑测试套件' : '➕ 创建测试套件'"
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
          <n-form-item label="套件名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="例如：核心交易流程回归赛道" />
          </n-form-item>
          <n-form-item label="套件描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="简述套件覆盖的业务场景..."
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
          
          <div style="background: var(--color-bg); padding: 16px 20px; border-radius: 12px; margin-top: 8px;">
            <n-form-item label="选择关联用例 (可多选)" path="test_case_ids" style="margin-bottom: 0;">
              <n-transfer
                v-model:value="formValue.test_case_ids"
                :options="testCaseOptions"
                source-title="项目中可选的用例"
                target-title="套件包含的用例"
                filterable
              />
            </n-form-item>
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

const message = useMessage()
const loading = ref(false)
const testSuites = ref<TestSuite[]>([])
const projects = ref<any[]>([])
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
  name: { required: true, message: '请输入套件名称', trigger: 'blur' }
}

const columns: DataTableColumns<TestSuite> = [
  { title: '套件名称', key: 'name', minWidth: 200 },
  { title: '业务描述', key: 'description' },
  { 
    title: '包含用例数', 
    key: 'test_cases',
    width: 120,
    render(row) {
      return h('span', { style: 'font-weight: 600; color: var(--color-primary);' }, `${row.test_cases?.length || 0} 个`)
    }
  },
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
    width: 200,
    fixed: 'right' as const,
    render(row) {
      return h(NSpace, { align: 'center', wrap: false }, {
        default: () => [
          h(NButton, { size: 'small', type: 'primary', onClick: () => handleRun(row) }, { default: () => '触发运行' }),
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
    message.error('获取套件列表失败')
  } finally {
    loading.value = false
  }
}

const fetchTestCases = async () => {
  if (!selectedProjectId.value) return
  try {
    // 简化获取当前项目所有用例（通过模块）
    const modulesRes = await api.get(`/modules/?project_id=${selectedProjectId.value}`)
    let allCases: any[] = []
    // 注意：如果有大量数据，这种串行请求不推荐。但作为 Demo 可以接受
    const mPromises = modulesRes.data.map((m: any) => api.get(`/cases/?module_id=${m.id}`))
    const results = await Promise.all(mPromises)
    results.forEach(res => {
      allCases = [...allCases, ...res.data]
    })
    
    testCaseOptions.value = allCases.map(c => ({ label: c.name, value: c.id }))
  } catch (error) {
    message.error('加载项目下所有用例失败')
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
          message.success('套件信息修改成功')
        } else {
          await api.post('/suites/', data)
          message.success('新套件已创建')
        }
        handleCloseModal()
        fetchTestSuites()
      } catch (error) {
        message.error(editingId.value ? '保存失败' : '创建失败')
      }
    }
  })
}

const handleEdit = async (row: TestSuite) => {
  await fetchTestCases()
  editingId.value = row.id
  formValue.value = {
    name: row.name,
    description: row.description || '',
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
    message.success('套件已删除')
    fetchTestSuites()
  } catch (error) {}
}

const handleRun = async (row: TestSuite) => {
  try {
    message.info('正在分发套件运行任务...')
    const response = await api.post(`/execution/suites/${row.id}/run`)
    if (response.data.task_id) {
      message.success('套件任务已推入执行队列，请到报告页查看进度')
    } else {
      message.error(`下发任务异常: ${response.data.message || '未知错误'}`)
    }
  } catch (error) {
    message.error('套件触发失败，这可能是网络或服务问题')
  }
}

onMounted(() => fetchProjects())
</script>

<style scoped>
.card-wrap {
  background: var(--color-card);
  border-radius: 16px;
  border: 1px solid var(--color-divider);
  padding: 4px;
  overflow: hidden;
}
</style>
