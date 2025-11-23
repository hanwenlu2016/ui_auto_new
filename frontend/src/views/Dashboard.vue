<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h1>数据概览</h1>
      <p>实时监控您的测试自动化平台</p>
    </div>
    
    <n-grid :x-gap="16" :y-gap="16" :cols="4" class="stats-grid">
      <n-grid-item>
        <n-card class="stat-card stat-card-1" :bordered="false">
          <div class="stat-info">
            <div class="stat-label">项目数</div>
            <div class="stat-value">12</div>
          </div>
          <div class="stat-icon">📊</div>
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card class="stat-card stat-card-2" :bordered="false">
          <div class="stat-info">
            <div class="stat-label">测试用例</div>
            <div class="stat-value">156</div>
          </div>
          <div class="stat-icon">📝</div>
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card class="stat-card stat-card-3" :bordered="false">
          <div class="stat-info">
            <div class="stat-label">执行次数</div>
            <div class="stat-value">45</div>
          </div>
          <div class="stat-icon">🚀</div>
        </n-card>
      </n-grid-item>
      <n-grid-item>
        <n-card class="stat-card stat-card-4" :bordered="false">
          <div class="stat-info">
            <div class="stat-label">通过率</div>
            <div class="stat-value">92%</div>
          </div>
          <div class="stat-icon">✅</div>
        </n-card>
      </n-grid-item>
    </n-grid>
    
    <n-card title="最近活动" class="activity-card" :bordered="false">
      <template #header-extra>
        <n-button text type="primary">查看全部</n-button>
      </template>
      <n-empty description="暂无活动" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { NGrid, NGridItem, NCard, NEmpty, NButton } from 'naive-ui'
import { onMounted } from 'vue'

// Counter animation
onMounted(() => {
  const counters = document.querySelectorAll('.counter')
  counters.forEach((counter) => {
    const target = parseInt(counter.getAttribute('data-target') || '0')
    const duration = 2000
    const step = target / (duration / 16)
    let current = 0
    
    const timer = setInterval(() => {
      current += step
      if (current >= target) {
        counter.textContent = target.toString()
        clearInterval(timer)
      } else {
        counter.textContent = Math.floor(current).toString()
      }
    }, 16)
  })
})
</script>
<style scoped>
.dashboard-container {
  padding: 16px;
}

.dashboard-header {
  margin-bottom: 16px;
}

.dashboard-header h1 {
  font-size: 20px;
  font-weight: 500;
  color: #1f2225;
  margin: 0 0 4px 0;
}

.dashboard-header p {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.stats-grid {
  margin-bottom: 16px;
}

.stat-card {
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.stat-card:hover {
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
}

.stat-card :deep(.n-card__content) {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 14px;
  color: #808695;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 30px;
  font-weight: 500;
  color: #17233d;
  line-height: 1;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.stat-card-1 .stat-icon {
  background: #e6f7ff;
  color: #1890ff;
}

.stat-card-2 .stat-icon {
  background: #fff7e6;
  color: #fa8c16;
}

.stat-card-3 .stat-icon {
  background: #f6ffed;
  color: #52c41a;
}

.stat-card-4 .stat-icon {
  background: #fff0f6;
  color: #eb2f96;
}

.activity-card {
  border-radius: 4px;
}

.activity-card :deep(.n-card-header) {
  padding: 16px 20px;
  border-bottom: 1px solid #e8eaec;
}

.activity-card :deep(.n-card__content) {
  padding: 0;
}
</style>
