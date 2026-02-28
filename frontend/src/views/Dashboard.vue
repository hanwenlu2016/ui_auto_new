<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1>数据概览</h1>
        <p>实时监控您的 UI 自动化测试平台</p>
      </div>
    </div>

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div
        v-for="(stat, i) in stats"
        :key="i"
        class="stat-card card-hoverable animate-fade-up"
        :style="{ animationDelay: `${i * 0.06}s` }"
      >
        <div class="stat-icon" :style="{ background: stat.iconBg }">
          <span>{{ stat.icon }}</span>
        </div>
        <div class="stat-body">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value" :style="{ background: stat.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }">
            {{ stat.value }}
          </div>
        </div>
        <div class="stat-trend" :class="stat.trend >= 0 ? 'trend-up' : 'trend-down'">
          {{ stat.trend >= 0 ? '↑' : '↓' }} {{ Math.abs(stat.trend) }}%
        </div>
      </div>
    </div>

    <!-- Quick actions -->
    <div class="section-title">快捷操作</div>
    <div class="quick-actions">
      <div
        v-for="(action, i) in quickActions"
        :key="i"
        class="quick-action-card card-hoverable animate-fade-up"
        :style="{ animationDelay: `${0.25 + i * 0.07}s` }"
        @click="action.handler"
      >
        <div class="action-icon" :style="{ background: action.iconBg }">{{ action.icon }}</div>
        <div class="action-label">{{ action.label }}</div>
        <div class="action-desc">{{ action.desc }}</div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="section-title" style="margin-top: 24px">最近活动</div>
    <div class="activity-card animate-fade-up" style="animation-delay: 0.5s">
      <div v-if="recentActivities.length === 0" class="empty-wrap">
        <div style="font-size: 36px; margin-bottom: 12px; opacity:0.5">📋</div>
        <div style="font-size: 14px; color: var(--color-text-3)">暂无最近活动</div>
      </div>
      <div v-else class="activity-list">
        <div v-for="act in recentActivities" :key="act.id" class="activity-item">
          <div class="activity-status" :class="act.status === 'success' ? 'status-success' : 'status-error'">
            {{ act.status === 'success' ? '✅' : '❌' }}
          </div>
          <div class="activity-content">
            <div class="activity-desc">{{ act.desc }}</div>
            <div class="activity-time">{{ new Date(act.time).toLocaleString() }}</div>
          </div>
          <n-button v-if="act.url" text type="primary" size="small" @click="openReport(act.url)">查看报告</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import api from '@/api'

const router = useRouter()

const stats = ref([
  {
    label: '项目总数',
    value: '-',
    icon: '🗂',
    iconBg: 'rgba(79,129,255,0.1)',
    gradient: 'var(--gradient-blue)',
    trend: 0
  },
  {
    label: '测试用例',
    value: '-',
    icon: '📝',
    iconBg: 'rgba(251,146,60,0.1)',
    gradient: 'var(--gradient-amber)',
    trend: 0
  },
  {
    label: '执行次数',
    value: '-',
    icon: '🚀',
    iconBg: 'rgba(52,211,153,0.1)',
    gradient: 'var(--gradient-green)',
    trend: 0
  },
  {
    label: '通过率',
    value: '-',
    icon: '✅',
    iconBg: 'rgba(167,139,250,0.1)',
    gradient: 'var(--gradient-purple)',
    trend: 0
  }
])

const recentActivities = ref<any[]>([])

const fetchDashboardData = async () => {
  try {
    const statsRes = await api.get('/dashboard/stats')
    const data = statsRes.data
    stats.value[0].value = data.projects.toString()
    stats.value[1].value = data.cases.toString()
    stats.value[2].value = data.executions.toString()
    stats.value[3].value = data.success_rate.toString()

    const activitiesRes = await api.get('/dashboard/activities')
    recentActivities.value = activitiesRes.data
  } catch (err) {
    console.error('获取仪表板数据失败', err)
  }
}

const openReport = (url: string) => {
  window.open(`http://localhost:8000${url}`, '_blank')
}

onMounted(() => {
  fetchDashboardData()
})

const quickActions = [
  {
    label: '新建项目',
    desc: '创建一个新的测试项目',
    icon: '➕',
    iconBg: 'rgba(79,129,255,0.12)',
    handler: () => router.push({ name: 'Projects' })
  },
  {
    label: '开始录制',
    desc: '录制浏览器操作生成用例',
    icon: '⏺',
    iconBg: 'rgba(239,68,68,0.1)',
    handler: () => router.push({ name: 'Recording' })
  },
  {
    label: '查看报告',
    desc: '浏览最新的测试执行报告',
    icon: '📊',
    iconBg: 'rgba(52,211,153,0.1)',
    handler: () => router.push({ name: 'Reports' })
  },
  {
    label: '测试用例',
    desc: '管理和运行测试用例',
    icon: '🧪',
    iconBg: 'rgba(251,146,60,0.1)',
    handler: () => router.push({ name: 'TestCases' })
  }
]
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 22px 20px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  position: relative;
  border: 1px solid var(--color-divider);
  overflow: hidden;
}

.stat-card::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--gradient-blue);
  opacity: 0;
  transition: opacity 0.25s;
}

.stat-card:hover::after {
  opacity: 1;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}

.stat-body {
  flex: 1;
  min-width: 0;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-3);
  font-weight: 500;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -1px;
}

.stat-trend {
  position: absolute;
  top: 16px;
  right: 16px;
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 20px;
}

.trend-up {
  background: rgba(52, 211, 153, 0.12);
  color: #10B981;
}

.trend-down {
  background: rgba(239, 68, 68, 0.1);
  color: #EF4444;
}

/* Section title */
.section-title {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--color-text-3);
  margin-bottom: 12px;
}

/* Quick actions */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

.quick-action-card {
  background: #ffffff;
  border-radius: 14px;
  padding: 20px 18px;
  cursor: pointer;
  border: 1.5px solid transparent;
  transition: border-color 0.2s;
}

.quick-action-card:hover {
  border-color: var(--color-primary);
}

.action-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-bottom: 12px;
}

.action-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-1);
  margin-bottom: 4px;
}

.action-desc {
  font-size: 12px;
  color: var(--color-text-3);
  line-height: 1.5;
}

/* Activity */
.activity-card {
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid var(--color-divider);
  overflow: hidden;
}

.activity-list {
  display: flex;
  flex-direction: column;
}

.activity-item {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-divider);
  transition: background-color 0.2s;
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-item:hover {
  background-color: #fcfcfc;
}

.activity-status {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  margin-right: 14px;
}

.status-success {
  background: rgba(52,211,153,0.15);
}

.status-error {
  background: rgba(239,68,68,0.15);
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-desc {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-1);
  margin-bottom: 2px;
}

.activity-time {
  font-size: 12px;
  color: var(--color-text-3);
}

.empty-wrap {
  text-align: center;
  padding: 60px 0;
}

/* Responsive */
@media (max-width: 1100px) {
  .stats-grid,
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .stats-grid,
  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
