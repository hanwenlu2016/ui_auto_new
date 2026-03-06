<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1>报告管理</h1>
        <p>查看历史测试执行结果与生成的 Allure 测试报告</p>
      </div>
    </div>

    <div class="card-wrap shadow-sm animate-fade-up" style="animation-delay: 0.1s; padding: 0;">
      <n-data-table 
        :columns="columns" 
        :data="reports" 
        :loading="loading" 
        size="small"
        :bordered="false"
        class="custom-table"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NDataTable, NButton, NSpace, NTag, type DataTableColumns } from 'naive-ui'
import api from '@/api'

interface Report {
  id: number
  test_case_name?: string
  executor_name?: string
  status: string
  report_path: string
  report_url?: string
  created_at: string
}

const message = useMessage()
const loading = ref(false)
const reports = ref<Report[]>([])

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).replace(/\//g, '-')
}

const columns: DataTableColumns<Report> = [
  { title: '报告 ID', key: 'id', width: 80 },
  { title: '用例名称', key: 'test_case_name', minWidth: 250 },
  { title: '执行人', key: 'executor_name', width: 140 },
  { 
    title: '状态', 
    key: 'status', 
    width: 90,
    render(row: Report) {
      return h(NTag, {
        type: row.status === 'success' ? 'success' : 'error',
        bordered: false,
        size: 'small',
        round: true,
        style: 'font-size: 11px; height: 20px; line-height: 20px;'
      }, { default: () => row.status === 'success' ? '通过' : '失败' })
    }
  },
  { 
    title: '创建时间', 
    key: 'created_at', 
    width: 170,
    render(row: Report) {
      return formatDate(row.created_at)
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render(row: Report) {
      return h(NSpace, { align: 'center', size: 12 }, {
        default: () => [
          h(NButton, {
            size: 'small',
            type: 'primary',
            quaternary: true,
            disabled: !row.report_url,
            style: 'font-size: 12px; padding: 0 4px;',
            onClick: () => {
              if (row.report_url) {
                window.open(row.report_url, '_blank')
              } else {
                message.warning('报告文件不存在')
              }
            }
          }, { default: () => '查看详情' }),
          h(NButton, {
            size: 'small',
            type: 'error',
            quaternary: true,
            style: 'font-size: 12px; padding: 0 4px;',
            onClick: () => deleteReport(row.id)
          }, { default: () => '删除' })
        ]
      })
    }
  }
]

async function fetchReports() {
  loading.value = true
  try {
    const res = await api.get('/reports/')
    reports.value = res.data
  } catch (e) {
    message.error('获取报告列表失败')
  } finally {
    loading.value = false
  }
}

async function deleteReport(id: number) {
  try {
    await api.delete(`/reports/${id}`)
    message.success('报告已删除')
    fetchReports()
  } catch (e) {
    message.error('删除报告失败')
  }
}

onMounted(() => {
  fetchReports()
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
