<template>
  <div class="reports-page">
    <n-card title="测试报告列表" style="margin: 20px;">
      <n-data-table :columns="columns" :data="reports" :loading="loading" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { useMessage, NCard, NDataTable, NButton, NSpace, NTag } from 'naive-ui'
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

const columns = [
  { title: '报告 ID', key: 'id', width: 80 },
  { title: '用例名称', key: 'test_case_name', width: 200 },
  { title: '执行人', key: 'executor_name', width: 150 },
  { 
    title: '状态', 
    key: 'status', 
    width: 100,
    render(row: Report) {
      return h(NTag, {
        type: row.status === 'success' ? 'success' : 'error',
        bordered: false
      }, { default: () => row.status })
    }
  },
  { 
    title: '创建时间', 
    key: 'created_at', 
    width: 180,
    render(row: Report) {
      return formatDate(row.created_at)
    }
  },
  {
    title: '操作',
    key: 'actions',
    render(row: Report) {
      return h(NSpace, null, {
        default: () => [
          h(NButton, {
            size: 'small',
            type: 'primary',
            disabled: !row.report_url,
            onClick: () => {
              if (row.report_url) {
                // Use backend URL + report_url
                const url = `http://localhost:8000${row.report_url}`
                window.open(url, '_blank')
              } else {
                message.warning('报告文件不存在')
              }
            }
          }, { default: () => '查看' }),
          h(NButton, {
            size: 'small',
            type: 'error',
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
.reports-page {
  padding: 20px;
}
</style>
