<template>
  <div class="recording-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>录制回放</h1>
        <p>在线录制用户操作并生成测试用例</p>
      </div>
    </div>

    <n-grid :cols="24" :x-gap="24">
      <n-grid-item :span="24">
        <n-card :bordered="false" class="control-card">
          <n-input-group>
            <n-input 
              v-model:value="url" 
              placeholder="请输入要录制的网址 (例如: https://example.com)" 
              :disabled="isRecording" 
              size="large"
            >
              <template #prefix>
                <span>🔗</span>
              </template>
            </n-input>
            <n-button 
              :type="isRecording ? 'error' : 'primary'" 
              @click="toggleRecording"
              size="large"
              style="width: 120px"
            >
              {{ isRecording ? '停止录制' : '开始录制' }}
            </n-button>
          </n-input-group>
        </n-card>
      </n-grid-item>

      <n-grid-item :span="24">
        <n-card title="录制事件" :bordered="false" class="events-card">
          <template #header-extra>
            <n-tag type="info" v-if="events.length > 0">
              共 {{ events.length }} 个事件
            </n-tag>
          </template>
          
          <div class="events-container">
            <n-scrollbar style="max-height: 500px">
              <n-timeline v-if="events.length > 0">
                <n-timeline-item
                  v-for="(event, index) in events"
                  :key="index"
                  type="success"
                  :title="event.action"
                  :content="`${event.selector} ${event.value ? '- ' + event.value : ''}`"
                  :time="new Date().toLocaleTimeString()"
                />
              </n-timeline>
              <n-empty v-else description="暂无录制事件，请开始录制" />
            </n-scrollbar>
          </div>
        </n-card>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from 'vue'
import { useMessage, NCard, NInputGroup, NInput, NButton, NScrollbar, NTimeline, NTimelineItem, NGrid, NGridItem, NTag, NEmpty } from 'naive-ui'

const message = useMessage()
const url = ref('https://example.com')
const isRecording = ref(false)
const events = ref<any[]>([])
let ws: WebSocket | null = null

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws`
  
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('WebSocket connected')
  }
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.status === 'started') {
      isRecording.value = true
      message.success('录制已开始')
    } else if (data.status === 'stopped') {
      isRecording.value = false
      message.success('录制已停止')
    } else if (data.action) {
      events.value.push(data)
    }
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    message.error('WebSocket 连接错误')
    isRecording.value = false
  }
  
  ws.onclose = () => {
    console.log('WebSocket disconnected')
    isRecording.value = false
  }
}

const toggleRecording = () => {
  if (!isRecording.value) {
    if (!url.value) {
      message.warning('请输入网址')
      return
    }
    events.value = []
    connectWebSocket()
    // In a real implementation, we would send a start message to the backend
    // For now, we simulate it via WebSocket connection logic or assume backend handles it on connect
    // But typically we need to send a message
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ action: 'start', url: url.value }))
    } else {
      // Wait for connection if just created
      setTimeout(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'start', url: url.value }))
        }
      }, 1000)
    }
  } else {
    if (ws) {
      ws.send(JSON.stringify({ action: 'stop' }))
      ws.close()
    }
    isRecording.value = false
  }
}

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>

<style scoped>
.recording-container {
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

.control-card {
  border-radius: 4px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
  margin-bottom: 16px;
}

.control-card :deep(.n-card__content) {
  padding: 24px;
}

.events-card {
  border-radius: 4px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
}

.events-card :deep(.n-card-header) {
  padding: 16px 24px;
  border-bottom: 1px solid #e8eaec;
  font-size: 16px;
  font-weight: 500;
}

.events-container {
  padding: 8px 0;
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
