<template>
  <div class="ai-assistant-wrapper">
    <!-- Floating Trigger Button -->
    <div class="ai-float-trigger" @click="isOpen = true">
      <div class="trigger-content">
        <n-icon size="24"><sparkles-icon /></n-icon>
        <span class="trigger-text">AI 助手</span>
      </div>
    </div>
  
    <!-- Centered AI Modal -->
    <n-modal
      v-model:show="isOpen"
      preset="card"
      :mask-closable="true"
      :closable="true"
      transform-origin="center"
      style="width: 1000px; max-width: 95vw; border-radius: 16px; overflow: hidden;"
    >
      <template #header>
        <div class="modal-header">
          <div class="header-left">
            <n-icon size="26" color="var(--color-primary)"><smart-icon /></n-icon>
            <span class="title-text">Aurora AI 智能助手</span>
          </div>
          <div v-if="appStore.selectedProjectId" class="project-badge">
            <div class="pulse-dot"></div>
            <span>知识库已激活: {{ connectedProjectName || '加载中...' }}</span>
          </div>
        </div>
      </template>

      <!-- Chat Area -->
      <div class="modal-body-content">
        <div class="chat-viewport" ref="historyRef">
          <div v-if="messages.length === 0" class="empty-state">
            <div class="empty-icon">✨</div>
            <h3 class="empty-title">您可以这样问我...</h3>
            <div class="suggestion-list">
              <div class="suggestion-item" @click="prompt = '打开百度，搜索“AI 自动化”'">“打开百度，搜索...”</div>
              <div class="suggestion-item" @click="prompt = '跳转到登录页，输入 admin/admin 并点击登录'">“自动执行登录流程...”</div>
            </div>
          </div>
          
          <div v-for="(msg, i) in messages" :key="i" class="message-block" :class="msg.role">
            <div class="message-content">
              <div class="text-payload">{{ msg.text }}</div>
              
              <!-- Standard Steps List (Happy Path) -->
              <div v-if="msg.steps && msg.steps.length > 0" class="steps-box">
                <div class="mini-steps">
                  <div v-for="(step, si) in msg.steps" :key="si" class="mini-step-item">
                    <div class="mini-step-content">
                      <n-tag :type="getActionType(step.action)" size="small">{{ mapActionIcon(step.action) }}</n-tag>
                      <span class="desc">{{ step.description || step.target }}</span>
                      <n-tag v-if="step.element_id" size="tiny" type="success" :bordered="false" class="match-badge">
                        ✓ 匹配元素库
                      </n-tag>
                    </div>
                  </div>
                </div>
                <n-button type="primary" secondary block size="small" @click="useSteps(msg.steps)" style="margin-top: 10px">🚀 立即导入步骤</n-button>
              </div>

            </div>
          </div>
          
          <div v-if="loading" class="message-block ai">
            <div class="message-content loading-state">
              <n-spin size="small" />
              <span>{{ 'AI 正在探索推演中...' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <template #footer>
        <div class="modal-footer-box">
          <div class="toolbar">
            <n-select
              v-model:value="selectedAIModel"
              :options="aiModelOptions"
              size="small"
              style="width: 160px"
              placeholder="AI 引擎"
            />
          </div>
          <div class="input-container">
            <n-input
              v-model:value="prompt"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 10 }"
              placeholder="请详细描述您想自动化的操作流程..."
              @keydown.enter.prevent="handleSend"
              style="font-size: 15px; border-radius: 12px; border: 1px solid var(--color-divider);"
            />
            <n-button 
              type="primary" 
              circle 
              :disabled="!prompt.trim() || loading" 
              @click="handleSend"
              class="send-btn"
            >
              <template #icon><n-icon size="24"><send-icon /></n-icon></template>
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NButton, NInput, NSpin, NTag, NSelect, useMessage, NModal } from 'naive-ui'
import { 
  SparklesOutline as SparklesIcon, 
  PlanetOutline as SmartIcon,
  PaperPlaneOutline as SendIcon
} from '@vicons/ionicons5'
import api from '@/api'
import { useRecordingStore } from '@/stores/recording'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const recordingStore = useRecordingStore()
const appStore = useAppStore()
const isOpen = ref(false)
const prompt = ref('')
const loading = ref(false)
const historyRef = ref<HTMLElement | null>(null)
const messages = ref<any[]>([])
const message = useMessage()
const aiModelOptions = ref<any[]>([])
const selectedAIModel = ref<string | null>(null)
const connectedProjectName = ref('')

// Fetch project name for status bar
const fetchProjectName = async () => {
  if (appStore.selectedProjectId) {
    try {
      const res = await api.get(`/projects/${appStore.selectedProjectId}`)
      connectedProjectName.value = res.data.name
    } catch {
      connectedProjectName.value = '未知项目'
    }
  }
}

// Watch project switch to re-fetch name
watch(() => appStore.selectedProjectId, fetchProjectName, { immediate: true })

const scrollToBottom = async () => {
  await nextTick()
  if (historyRef.value) historyRef.value.scrollTop = historyRef.value.scrollHeight
}

const handleSend = async () => {
  if (!prompt.value.trim() || loading.value) return
  
  const userText = prompt.value
  messages.value.push({ role: 'user', text: userText })
  prompt.value = ''
  loading.value = true
  
  await scrollToBottom()
  
  try {
    const msgObj = {
      role: 'ai',
      text: '正在智能推演自动化流程...',
      steps: []
    }
    const messageIndex = messages.value.push(msgObj) - 1
    
    try {
      const response = await fetch('/api/v1/agent/execute_stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          task: userText,
          model_id: selectedAIModel.value,
          headless: true,
          max_steps: 20,
          project_id: appStore.selectedProjectId
        })
      })

      if (!response.ok) throw new Error('大模型请求失败，请检查模型额度与网络')
      const reader = response.body?.getReader()
      if (!reader) throw new Error('流读取器加载失败')
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.trim()) continue
          try {
            const item = JSON.parse(line)
            const currentMsg = { ...messages.value[messageIndex] }
            if (item.type === 'step') {
              currentMsg.steps = [...(currentMsg.steps || []), item.data]
              currentMsg.text = `正在执行第 ${item.step_number} 步...`
            } else if (item.type === 'done') {
              currentMsg.text = `智能推演执行完毕，已完美提取 ${item.total_steps} 个步骤。`
            } else if (item.type === 'error') {
              currentMsg.text = `执行异常: ${item.message}`
            }
            messages.value[messageIndex] = currentMsg
            await scrollToBottom()
          } catch (e) {}
        }
      }
    } catch (err: any) {
      messages.value[messageIndex].text = `执行失败: ${err.message}`
    }
  } catch (err: any) {
    messages.value.push({ role: 'ai', text: '请求异常，请检查配置或重试' })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const getActionType = (action: string) => {
  const map: any = { 'goto': 'info', 'click': 'primary', 'fill': 'warning', 'assert_text': 'success' }
  return map[action] || 'default'
}

const mapActionIcon = (action: string) => {
  const icons: any = { 'goto': '🔗 跳转', 'click': '🖱️ 点击', 'fill': '⌨️ 输入', 'assert_text': '✅ 断言' }
  return icons[action] || '⚡ ' + action
}

const useSteps = (steps: any[]) => {
  recordingStore.setPendingSteps(steps)
  window.dispatchEvent(new CustomEvent('ai-use-steps', { detail: steps }))
  isOpen.value = false
  message.success('步骤已导入，正在跳转...')
  router.push('/recording')
}

const fetchModels = async () => {
  try {
    const res = await api.get('/ai-models/')
    aiModelOptions.value = res.data.map((m: any) => ({ label: m.name, value: String(m.id) }))
    if (res.data.length > 0) selectedAIModel.value = String(res.data[0].id)
  } catch (e) {}
}

onMounted(fetchModels)
watch(isOpen, val => val && nextTick(scrollToBottom))
</script>

<style scoped>
.ai-assistant-wrapper {
  position: fixed;
  right: 0;
  bottom: 80px;
  z-index: 2000;
}

.ai-float-trigger {
  background: #3b82f6; /* 强制亮蓝色 */
  color: #ffffff;
  padding: 14px 24px;
  border-radius: 40px 0 0 40px;
  box-shadow: -8px 0 30px rgba(59, 130, 246, 0.3);
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  border: 1px solid rgba(255,255,255,0.3);
  border-right: none;
}

.ai-float-trigger:hover {
  transform: translateX(-10px);
  padding-right: 34px;
  background: var(--color-primary-hover);
}

.trigger-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.trigger-text {
  font-weight: 700;
  font-size: 15px;
  letter-spacing: 0.5px;
}

.modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-text {
  font-weight: 800;
  font-size: 18px;
  background: linear-gradient(90deg, var(--color-primary), #8e2de2);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.project-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #ecfdf5;
  color: #059669;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid #10b981;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 0 rgba(16, 185, 129, 0.4);
  animation: pulseGreen 2s infinite;
}

@keyframes pulseGreen {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.modal-body-content {
  height: 500px;
  background: #f1f5f9; /* 浅灰色底色，让白色气泡更醒目 */
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
}

.chat-viewport {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-block { display: flex; width: 100%; }
.message-block.user { justify-content: flex-end; }
.message-block.ai { justify-content: flex-start; }

.message-content {
  max-width: 80%;
  padding: 14px 18px;
  border-radius: 18px;
  font-size: 14px;
  line-height: 1.6;
  color: #1e293b !important; /* 强制深色文字 */
}

.user .message-content {
  background: var(--color-primary);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(79, 129, 255, 0.2);
}

.ai .message-content {
  background: white;
  border: 1px solid #cbd5e1;
  border-bottom-left-radius: 4px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #718096;
}

.modal-footer-box {
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}



.input-container {
  display: flex;
  align-items: flex-end;
  gap: 16px;
}

.send-btn {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(79, 129, 255, 0.3);
}

.empty-state { text-align: center; padding: 60px 20px; }
.empty-icon { font-size: 56px; margin-bottom: 20px; }
.empty-title { color: #0f172a; margin-bottom: 24px; font-weight: 700; }
.suggestion-list { display: flex; flex-direction: column; gap: 12px; max-width: 400px; margin: 0 auto; }
.suggestion-item {
  background: white;
  border: 1px solid #94a3b8; /* 更深的边框 */
  padding: 14px;
  border-radius: 12px;
  font-size: 13px;
  color: #1e293b !important; /* 强制深黑文字 */
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.suggestion-item:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  background: #f0f7ff;
}

.mini-step-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: #4a5568;
}

.mini-step-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.match-badge {
  font-weight: 700;
  font-size: 10px;
  padding: 0 4px;
}
</style>
