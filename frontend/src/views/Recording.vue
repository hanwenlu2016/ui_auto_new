<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1>录制回放</h1>
        <p>在线录制浏览器操作并一键生成测试用例</p>
      </div>
    </div>

    <n-grid :cols="24" :x-gap="24" :y-gap="24">
      <!-- Control Panel -->
      <n-grid-item :span="24">
        <div class="card-wrap shadow-sm popup-card">
          <div style="font-size: 14px; font-weight: 600; color: var(--color-text-1); margin-bottom: 16px;">配置与控制</div>
          <n-input-group style="display: flex; gap: 12px; background: transparent;">
            <n-select
              v-model:value="selectedProjectId"
              :options="projectOptions"
              placeholder="选择关联项目"
              style="width: 220px;"
              :disabled="isRecording"
            />
            <n-input 
              v-model:value="url" 
              placeholder="https://example.com" 
              :disabled="isRecording" 
              style="flex: 1;"
            >
              <template #prefix>
                <span style="color: var(--color-text-3);">🌐</span>
              </template>
            </n-input>
            
            <n-button 
              :type="isRecording ? 'error' : 'primary'" 
              @click="toggleRecording"
              style="min-width: 140px; font-weight: 600;"
              :class="isRecording ? 'pulse-anim' : ''"
            >
              <template #icon>
                <span class="icon-pulse">{{ isRecording ? '⏹' : '⏺' }}</span>
              </template>
              {{ isRecording ? '停止录制' : '开始录制' }}
            </n-button>
            <n-button
              type="success"
              secondary
              @click="showSaveModal = true"
              style="min-width: 140px; font-weight: 600;"
              :disabled="isRecording || events.length === 0"
            >
              <template #icon>💾</template>
              保存用例
            </n-button>
          </n-input-group>
        </div>
      </n-grid-item>

      <!-- Events List -->
      <n-grid-item :span="24">
        <div class="card-wrap shadow-sm popup-card events-card animate-fade-up" style="animation-delay: 0.1s">
          <div class="events-header">
            <div style="font-size: 14px; font-weight: 600; color: var(--color-text-1);">录制事件流</div>
            <n-tag type="info" size="small" :bordered="false" round v-if="events.length > 0">
              共 {{ events.length }} 个动作
            </n-tag>
            <n-tag v-if="isRecording" type="warning" size="small" :bordered="false" round ghost>
              ✨ AI 增强录制已启用
            </n-tag>
          </div>
          
          <div class="events-container">
            <n-scrollbar style="max-height: 50vh; padding-right: 16px;">
              <n-timeline v-if="events.length > 0" size="large">
                <n-timeline-item
                  v-for="(event, index) in events"
                  :key="index"
                  :type="getEventColor(event.action)"
                  :title="getEventTitle(event.action)"
                  :time="event.recordedAt || ''"
                >
                  <div class="event-payload">
                    <template v-if="event.action === 'goto'">
                      <span class="payload-label">网址:</span>
                      <span class="payload-val">{{ event.value }}</span>
                    </template>
                    <template v-else-if="event.action === 'wait'">
                      <span class="payload-label">时长:</span>
                      <span class="payload-val">{{ formatWaitSeconds(event) }}</span>
                    </template>
                    <template v-else-if="event.action === 'wait_for_selector'">
                      <span class="payload-label">目标:</span>
                      <span class="payload-val">{{ event.selector || '-' }}</span>
                      <span class="payload-label">超时:</span>
                      <span class="payload-val">{{ formatWaitForSelectorSeconds(event) }}</span>
                    </template>
                    <template v-else>
                      <div class="payload-row">
                        <span class="payload-target">{{ event.selector }}</span>
                        <n-tooltip trigger="hover" v-if="event.ai_reinforced">
                          <template #trigger>
                            <span class="ai-badge">✨ AI Reinforced</span>
                          </template>
                          <div class="ai-reasoning">
                            <div style="font-weight: bold; margin-bottom: 4px;">多级自愈定位链:</div>
                            <div v-for="(val, key) in event.locator_chain" :key="key" v-show="val">
                              <span style="opacity: 0.6">{{ key }}:</span> {{ val }}
                            </div>
                            <div v-if="event.confidence" style="margin-top: 4px; color: var(--color-primary);">
                              信心值: {{ (event.confidence * 100).toFixed(1) }}%
                            </div>
                          </div>
                        </n-tooltip>
                      </div>
                      <span v-if="event.value" class="payload-val" style="margin-top: 4px; display: block;">➔ {{ event.value }}</span>
                    </template>
                    <span v-if="event.description" class="payload-desc">{{ event.description }}</span>
                  </div>
                </n-timeline-item>
              </n-timeline>
              <div v-else class="empty-wrap">
                <div style="font-size: 40px; margin-bottom: 12px; opacity: 0.5;">⏺</div>
                <div style="font-size: 14px; color: var(--color-text-2);">等待录制动作...</div>
              </div>
            </n-scrollbar>
          </div>
        </div>
      </n-grid-item>
    </n-grid>

    <!-- Save Modal -->
    <n-modal v-model:show="showSaveModal">
      <n-card
        title="💾 保存为测试用例"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        style="width: 500px; max-width: 90vw;"
      >
        <n-form ref="formRef" :model="formValue" :rules="rules" label-placement="top">
          <n-form-item label="用例名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="请输入直观的用例名称" />
          </n-form-item>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <n-form-item label="归属模块" path="module_id">
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
                  { label: 'P0 核心', value: 'P0' },
                  { label: 'P1 重要', value: 'P1' },
                  { label: 'P2 一般', value: 'P2' }
                ]"
              />
            </n-form-item>
          </div>
          <n-form-item label="用例描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="简要描述（可选）"
              :autosize="{ minRows: 2, maxRows: 4 }"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="showSaveModal = false">取消</n-button>
            <n-button type="primary" @click="handleSave">确认保存</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>

    <!-- Modeling Modal -->
    <n-modal v-model:show="showModelingModal">
      <n-card
        title="✨ 一键沉淀页面元素"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        style="width: 600px; max-width: 90vw;"
      >
        <p>录制结束，我们在您的操作中发现了以下未入库的新元素。是否将其快捷加入项目资产库以供未来复用？</p>
        <div style="max-height: 300px; overflow-y: auto; margin-top: 16px;">
          <div v-for="(el, idx) in targetElements" :key="idx" style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px; padding: 8px; background: var(--color-bg); border-radius: 8px;">
            <n-checkbox v-model:checked="el.selected" />
            <n-input size="small" v-model:value="el.name" placeholder="元素名称" style="width: 140px;" />
            <div style="flex: 1; font-family: monospace; font-size: 12px; color: var(--color-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ el.selector }}
            </div>
            <n-tag size="small" type="info">{{ el.type }}</n-tag>
          </div>
        </div>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="showModelingModal = false">跳过</n-button>
            <n-button type="success" :loading="syncingElements" @click="handleSyncModeling">📥 同步入库</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>

  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, onMounted, watch } from 'vue'
import { useMessage, NCard, NInputGroup, NInput, NButton, NScrollbar, NTimeline, NTimelineItem, NGrid, NGridItem, NTag, NModal, NForm, NFormItem, NSelect, NCheckbox, type FormRules } from 'naive-ui'
import api from '@/api'
import { useRecordingStore } from '@/stores/recording'
import { useAppStore } from '@/stores/app'

const message = useMessage()
const recordingStore = useRecordingStore()
const appStore = useAppStore()

const url = ref('')
const isRecording = ref(false)
const events = ref<any[]>([])
let ws: WebSocket | null = null

const projects = ref<any[]>([])
const projectOptions = ref<{ label: string; value: number }[]>([])
const selectedProjectId = ref<number | null>(appStore.selectedProjectId)

const showSaveModal = ref(false)
const formRef = ref(null)
const moduleOptions = ref<{ label: string; value: number }[]>([])
const formValue = ref({
  name: '',
  module_id: appStore.selectedModuleId as number | null,
  priority: 'P1',
  description: ''
})

const showModelingModal = ref(false)
const targetElements = ref<any[]>([])
const syncingElements = ref(false)

const rules: FormRules = {

  name: { required: true, message: '请输入用例名称', trigger: 'blur' },
  module_id: { required: true, type: 'number', message: '请选择模块', trigger: 'change' }
}

const parseDurationToMs = (raw: any): number | null => {
  if (raw === null || raw === undefined) return null
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    return Math.round(raw >= 100 ? raw : raw * 1000)
  }
  const text = String(raw).trim().toLowerCase()
  if (!text) return null
  const m = text.match(/^(\d+(?:\.\d+)?)\s*(ms|s)?$/)
  if (!m) return null
  const amount = Number(m[1])
  const unit = m[2]
  if (unit === 'ms') return Math.round(amount)
  if (unit === 's') return Math.round(amount * 1000)
  return Math.round(amount >= 100 ? amount : amount * 1000)
}

const formatWaitSeconds = (event: any) => {
  const ms = parseDurationToMs(event?.wait_ms ?? event?.value)
  if (ms === null) return '-'
  return `${(ms / 1000).toFixed(1)}s`
}

const formatWaitForSelectorSeconds = (event: any) => {
  const ms = parseDurationToMs(event?.wait_ms ?? event?.value)
  return `${((ms ?? 8000) / 1000).toFixed(1)}s`
}

const inferLocatorType = (selector: string) => {
  const value = String(selector || '').trim()
  if (!value) return 'css'
  if (value.startsWith('//') || value.startsWith('xpath=')) return 'xpath'
  return 'css'
}

const buildDefaultEventDescription = (action: string, selector: string, value: string, waitMs: number | null) => {
  if (action === 'wait') return `等待 ${(waitMs ?? 1000) / 1000}s`
  if (action === 'wait_for_selector') return `等待元素出现: ${selector || '目标元素'} (超时 ${(waitMs ?? 8000) / 1000}s)`
  if (action === 'goto') return `访问页面 ${value || ''}`.trim()
  if (action === 'click') return `点击 ${selector || '目标元素'}`
  if (action === 'fill') return `输入 ${selector || '输入框'}`
  return ''
}

const fetchProjects = async () => {
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
    projectOptions.value = projects.value.map((p: any) => ({ label: p.name, value: p.id }))
    if (projects.value.length > 0) selectedProjectId.value = projects.value[0].id
  } catch (error) {}
}

watch(selectedProjectId, (newId) => {
  appStore.setProjectId(newId)
  if (newId) {
    const project = projects.value.find(p => p.id === newId)
    url.value = project && project.base_url ? project.base_url : ''
    fetchModules(newId)
  } else {
    url.value = ''
    moduleOptions.value = []
  }
})

watch(() => formValue.value.module_id, (newId) => {
  appStore.setModuleId(newId)
})

const fetchModules = async (projectId: number | null) => {
  if (!projectId) { moduleOptions.value = []; return }
  try {
    const response = await api.get(`/modules/?project_id=${projectId}`)
    moduleOptions.value = response.data.map((m: any) => ({ label: m.name, value: m.id }))
    if (moduleOptions.value.length > 0 && !formValue.value.module_id) {
       formValue.value.module_id = moduleOptions.value[0].value
    }
  } catch (error) {}
}

watch(showSaveModal, (show) => {
  if (show && selectedProjectId.value) fetchModules(selectedProjectId.value)
})

const handleSave = async () => {
  // @ts-ignore
  formRef.value?.validate(async (errors) => {
    if (!errors) {
      try {
        const steps = events.value.map(e => ({
          action: e.action,
          selector: e.selector,
          value: (e.action === 'wait' || e.action === 'wait_for_selector')
            ? String(parseDurationToMs(e.wait_ms ?? e.value) ?? (e.action === 'wait' ? 1000 : 8000))
            : (e.value || ''),
          wait_ms: (e.action === 'wait' || e.action === 'wait_for_selector')
            ? (parseDurationToMs(e.wait_ms ?? e.value) ?? (e.action === 'wait' ? 1000 : 8000))
            : null,
          description: e.description || '',
          page_id: e.page_id || null,
          element_id: e.element_id || null,
          metadata_json: e.metadata || null,
          locator_chain: e.locator_chain || null
        }))
        if (steps.length === 0) { message.warning('没有可保存的步骤'); return }

        const payload = { ...formValue.value, steps }
        await api.post('/cases/', payload)
        message.success('测试用例已成功保存')
        showSaveModal.value = false
        events.value = []
        formValue.value = { name: '', module_id: null, priority: 'P1', description: '' }
      } catch (error: any) {
        const detail = error?.response?.data?.detail
        message.error(detail ? `保存失败：${detail}` : '保存异常')
      }
    }
  })
}

// Recording Implementation (same as before)
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/recording/ws`
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => console.log('WebSocket connected')
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    if (data.status === 'started') {
      isRecording.value = true
      message.success('自动化引擎已启动')
    } else if (data.status === 'stopped') {
      isRecording.value = false
      message.success('已停止录制')
      handleRecordingStopped()
    } else if (data.status === 'error') {
      isRecording.value = false
      message.error(`引擎异常: ${data.message}`)
    } else if (data.action) {
      events.value.push({ 
        ...data, 
        recordedAt: new Date().toLocaleTimeString(),
        metadata: data.metadata || null
      })
    }
  }
  ws.onerror = () => { message.error('服务连接断开'); isRecording.value = false }
  ws.onclose = () => { isRecording.value = false }
}

const toggleRecording = () => {
  if (!isRecording.value) {
    if (!url.value) { message.warning('请先输入目标网址'); return }
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
    handleRecordingStopped()
  }
}

onMounted(() => {
  fetchProjects()
  window.addEventListener('ai-use-steps', handleAISteps as any)
  
  // Check for pending AI steps from other pages
  if (recordingStore.pendingSteps.length > 0) {
    handleAISteps({ detail: recordingStore.pendingSteps } as any)
    recordingStore.clearPendingSteps()
  }
})
onUnmounted(() => {
  if (ws) ws.close()
  window.removeEventListener('ai-use-steps', handleAISteps as any)
})

const handleAISteps = (e: CustomEvent) => {
  const steps = e.detail
  // 核心修复：每次导入新 AI 步骤前清空当前动作流，防止重复叠加
  events.value = []
  
  steps.forEach((s: any) => {
    const isWait = s.action === 'wait'
    const isWaitForSelector = s.action === 'wait_for_selector'
    const waitMs = (isWait || isWaitForSelector)
      ? (parseDurationToMs(s.wait_ms ?? s.value) ?? (isWait ? 1000 : 8000))
      : null
    const selector = s.target || s.selector || ''
    const value = (isWait || isWaitForSelector) ? String(waitMs) : (s.value || '')
    events.value.push({
      action: s.action,
      selector,
      value,
      wait_ms: waitMs,
      description: (s.description || '').trim() || buildDefaultEventDescription(s.action, selector, value, waitMs),
      page_id: s.page_id || null,
      element_id: s.element_id || null,
      locator_chain: s.locator_chain || null,
      recordedAt: new Date().toLocaleTimeString(),
      metadata: null // AI generated steps might not have metadata initially
    })
  })
}
const getEventColor = (action: string) => {
  const map: any = {
    'goto': 'info',
    'click': 'primary',
    'fill': 'warning',
    'wait': 'default',
    'wait_for_selector': 'default',
    'assert_text': 'success',
    'assert_visible': 'success',
    'select': 'secondary',
    'press': 'error',
    'screenshot': 'info',
    'hover': 'secondary'
  }
  return map[action] || 'info'
}

const handleRecordingStopped = () => {
    const newElements = events.value.filter((e: any) => e.selector && !e.element_id && ['click', 'fill', 'hover', 'select'].includes(e.action))
    if (newElements.length > 0) {
        const unique = []
        const seen = new Set()
        for (const el of newElements) {
            if (!seen.has(el.selector)) {
                seen.add(el.selector)
                unique.push({
                    name: el.description?.replace(/点击 |输入 |使用 \[[^\]]+\] -> /g, '').trim() || 'New Element',
                    selector: el.selector,
                    type: el.action,
                    selected: true,
                    locator_chain: el.locator_chain || null,
                    metadata_json: el.metadata || null,
                })
            }
        }
        targetElements.value = unique
        showModelingModal.value = true
    }
}

const handleSyncModeling = async () => {
    syncingElements.value = true
    const selected = targetElements.value.filter(el => el.selected)
    if (selected.length === 0) {
        showModelingModal.value = false
        syncingElements.value = false
        return
    }
    try {
        const pagesRes = await api.get(`/pages/?project_id=${selectedProjectId.value}`)
        let targetPageId = pagesRes.data?.[0]?.id

        if (!targetPageId) {
          const newPageRes = await api.post('/pages/', {
            name: 'Recording Discovered',
            project_id: selectedProjectId.value,
            module_id: formValue.value.module_id
          })
          targetPageId = newPageRes.data.id
        }

        for (const el of selected) {
          const metadataJson: Record<string, any> = {
            ...(el.metadata_json || {}),
            discovered: true,
            source: 'recording',
            action_type: el.type,
            selector_aliases: Array.from(new Set([
              el.selector,
              el.locator_chain?.primary,
              el.locator_chain?.fallback_1,
              el.locator_chain?.fallback_2,
              el.locator_chain?.fallback_3
            ].filter(Boolean)))
          }
          if (el.locator_chain) {
            metadataJson.locator_chain = el.locator_chain
          }
          await api.post('/elements/', {
            name: el.name,
            description: '',
            page_id: targetPageId,
            locator_type: inferLocatorType(el.selector),
            locator_value: el.selector,
            metadata_json: metadataJson
          })
        }
        message.success(`成功同步 ${selected.length} 个元素到资产库！这些元素现在可以在 AI 自然语言模式中直接被理解和精确调用。`)
        showModelingModal.value = false
    } catch (e) {
        message.error('同步失败')
    } finally {
        syncingElements.value = false
    }
}

const getEventTitle = (action: string) => {
  const map: any = {
    'goto': '🌐 访问页面',
    'click': '🖱️ 点击操作',
    'fill': '⌨️ 输入操作',
    'wait': '⏳ 等待时长',
    'wait_for_selector': '⏳ 等待元素',
    'assert_text': '✅ 文本断言',
    'assert_visible': '✅ 可见断言',
    'select': '📑 下拉选择',
    'press': '🪄 按键操作',
    'screenshot': '📸 截图',
    'hover': '🕒 悬停操作'
  }
  return map[action] || '🖱️ 动作'
}
</script>

<style scoped>
.card-wrap {
  background: var(--color-card);
  border-radius: 16px;
  border: 1px solid var(--color-divider);
}

.popup-card {
  padding: 24px;
}

.events-card {
  min-height: 400px;
}

.events-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--color-divider);
}

.event-payload {
  margin-top: 6px;
  background: var(--color-bg);
  padding: 8px 12px;
  border-radius: 6px;
  font-family: monospace;
  font-size: 13px;
  color: var(--color-text-2);
  display: inline-flex;
  gap: 8px;
  word-break: break-all;
}

.payload-target {
  color: #DDA0DD;
}

.payload-val {
  color: var(--color-primary);
  font-weight: 500;
}

.payload-desc {
  display: block;
  width: 100%;
  margin-top: 4px;
  color: var(--color-text-2);
}

.payload-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.ai-badge {
  font-size: 10px;
  background: linear-gradient(135deg, #6e8efb, #a777e3);
  color: white;
  padding: 1px 6px;
  border-radius: 10px;
  cursor: help;
  user-select: none;
  font-weight: 600;
  text-transform: uppercase;
}

.ai-reasoning {
  font-size: 12px;
  line-height: 1.6;
}

/* Animations */
@keyframes pulseRed {
  0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
  100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
}

.pulse-anim {
  animation: pulseRed 2s infinite;
}
</style>
