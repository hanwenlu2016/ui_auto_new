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
            <n-select
              v-model:value="selectedProjectId"
              :options="projectOptions"
              placeholder="选择项目"
              style="width: 200px"
              :disabled="isRecording"
            />
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
            <n-button
              type="success"
              @click="showSaveModal = true"
              size="large"
              style="width: 120px; margin-left: 12px;"
              :disabled="isRecording || events.length === 0"
            >
              保存用例
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

    <!-- Save Modal -->
    <n-modal v-model:show="showSaveModal" style="width: 600px">
      <n-card
        title="保存为测试用例"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <n-form ref="formRef" :model="formValue" :rules="rules" label-placement="top">
          <n-form-item label="用例名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="请输入测试用例名称" />
          </n-form-item>
          <n-form-item label="所属模块" path="module_id">
            <n-select
              v-model:value="formValue.module_id"
              :options="moduleOptions"
              placeholder="选择模块"
            />
          </n-form-item>
          <n-form-item label="优先级" path="priority">
            <n-select
              v-model:value="formValue.priority"
              :options="[
                { label: 'P0', value: 'P0' },
                { label: 'P1', value: 'P1' },
                { label: 'P2', value: 'P2' }
              ]"
            />
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="描述（可选）"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="showSaveModal = false">取消</n-button>
            <n-button type="primary" @click="handleSave">保存</n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, onMounted, watch } from 'vue'
import { useMessage, NCard, NInputGroup, NInput, NButton, NScrollbar, NTimeline, NTimelineItem, NGrid, NGridItem, NTag, NEmpty, NModal, NForm, NFormItem, NSelect, NSpace, type FormRules } from 'naive-ui'
import api from '@/api'

const message = useMessage()
const url = ref('')
const isRecording = ref(false)
const events = ref<any[]>([])
let ws: WebSocket | null = null

// Project Selection
const projects = ref<any[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(null)

// Save Implementation
const showSaveModal = ref(false)
const formRef = ref(null)
const moduleOptions = ref<{ label: string; value: number }[]>([])
const formValue = ref({
  name: '',
  module_id: null as number | null,
  priority: 'P1',
  description: ''
})

const rules: FormRules = {
  name: { required: true, message: '请输入用例名称', trigger: 'blur' },
  module_id: { required: true, type: 'number', message: '请选择模块', trigger: 'change' }
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
    projectOptions.value = projects.value.map((p: any) => ({
      label: p.name,
      value: p.id
    }))
    // Select first project by default if available
    if (projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].id
    }
  } catch (error) {
    message.error('获取项目列表失败')
  }
}

// Watch selected project to update URL
watch(selectedProjectId, (newId) => {
  if (newId) {
    const project = projects.value.find(p => p.id === newId)
    if (project && project.base_url) {
      url.value = project.base_url
    } else {
      url.value = ''
    }
  } else {
    url.value = ''
  }
})

const fetchModules = async (projectId: number | null) => {
  if (!projectId) {
    moduleOptions.value = []
    return
  }
  try {
    // Pass project_id to filter modules
    const response = await api.get(`/modules/?project_id=${projectId}`)
    moduleOptions.value = response.data.map((m: any) => ({
      label: m.name,
      value: m.id
    }))
    if (moduleOptions.value.length > 0) {
      formValue.value.module_id = moduleOptions.value[0].value
    } else {
       formValue.value.module_id = null
    }
  } catch (error) {
    message.error('获取模块列表失败')
  }
}

// Watch showSaveModal to fetch modules when opened
watch(showSaveModal, (show) => {
  if (show && selectedProjectId.value) {
    fetchModules(selectedProjectId.value)
  }
})

const handleSave = async () => {
  // @ts-ignore
  formRef.value?.validate(async (errors) => {
    if (!errors) {
      try {
        const steps = events.value.map(e => ({
          action: e.action,
          target: e.selector, // Map selector to target
          value: e.value || '',
          page_id: null,
          element_id: null
        }))
        
        // Ensure steps is not empty? Maybe add a check.
        if (steps.length === 0) {
          message.warning('没有可保存的步骤')
          return
        }

        const payload = {
          ...formValue.value,
          steps: steps
        }
        
        await api.post('/cases/', payload)
        message.success('测试用例保存成功')
        showSaveModal.value = false
        // Optionally navigate to test cases list
        // router.push('/cases') // Assuming /cases is the route
      } catch (error) {
        message.error('保存失败')
      }
    }
  })
}

// Recording Implementation
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/recording/ws`
  
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
    } else if (data.status === 'error') {
      isRecording.value = false
      message.error(`录制启动失败: ${data.message}`)
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
    
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'start', url: url.value }))
    } else {
      setTimeout(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'start', url: url.value }))
        }
      }, 1000)
    }
  } else {
    if (ws) {
      ws.send(JSON.stringify({ type: 'stop' }))
      ws.close()
    }
    isRecording.value = false
  }
}

onMounted(() => {
  fetchProjects()
  // fetchModules() - Removed, we fetch on modal open or project select
})

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
