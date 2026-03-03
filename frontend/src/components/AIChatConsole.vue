<template>
  <div class="ai-console" :class="{ 'is-open': isOpen }">
    <!-- Trigger Button - Only visible when closed -->
    <div class="ai-trigger" v-if="!isOpen" @click="isOpen = true">
      <div class="trigger-inner">
        <n-icon size="24"><sparkles-icon /></n-icon>
        <span class="trigger-label">
          <span>AI</span>
          <span>助手</span>
        </span>
      </div>
    </div>

    <!-- Console Panel -->
    <div class="ai-panel">
      <div class="panel-header">
        <div class="header-title">
          <n-icon size="20" color="var(--color-primary)"><smart-icon /></n-icon>
          <span>Aurora AI</span>
        </div>
        <n-button quirks circle quaternary @click="isOpen = false">
          <n-icon size="20"><close-icon /></n-icon>
        </n-button>
      </div>

      <div class="panel-content">
        <div class="chat-history" ref="historyRef">
          <div v-if="messages.length === 0" class="welcome-view">
            <div class="welcome-icon">✨</div>
            <h3>您可以这样问我...</h3>
            <div class="suggest-chips">
              <div class="chip" @click="prompt = '打开百度，搜索“AI 自动化”'">“打开百度，搜索...”</div>
              <div class="chip" @click="prompt = '跳转到登录页，输入 admin/admin 并点击登录'">“自动执行登录流程...”</div>
            </div>
          </div>
          
          <div v-for="(msg, i) in messages" :key="i" class="message-row" :class="msg.role">
            <div class="message-bubble">
              <div class="message-text">{{ msg.text }}</div>
              
              <!-- Generated Steps Preview -->
              <div v-if="msg.steps && msg.steps.length > 0" class="steps-preview">
                <div class="steps-header">规划了 {{ msg.steps.length }} 个自动化动作</div>
                <div class="steps-list">
                  <div v-for="(step, si) in msg.steps" :key="si" class="step-mini-card">
                    <n-tag :type="getActionType(step.action)" size="small" class="action-tag">
                      {{ step.action }}
                    </n-tag>
                    <span class="step-desc">{{ step.description || step.target }}</span>
                  </div>
                </div>
                <n-button type="primary" secondary block size="small" @click="useSteps(msg.steps)" style="margin-top: 12px">
                  🚀 立即导入步骤并开始
                </n-button>
              </div>
            </div>
          </div>
          
          <div v-if="loading" class="message-row ai">
            <div class="message-bubble loading-bubble">
              <n-spin size="small" />
              <span>AI 正在思考...</span>
            </div>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <n-input
          v-model:value="prompt"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="描述您想执行的操作..."
          @keydown.enter.prevent="handleSend"
        />
        <n-button type="primary" circle :disabled="!prompt.trim() || loading" @click="handleSend">
          <template #icon><n-icon><send-icon /></n-icon></template>
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NButton, NInput, NSpin, NTag, useMessage } from 'naive-ui'
import { 
  SparklesOutline as SparklesIcon, 
  CloseOutline as CloseIcon,
  PlanetOutline as SmartIcon,
  PaperPlaneOutline as SendIcon
} from '@vicons/ionicons5'
import api from '@/api'
import { useRecordingStore } from '@/stores/recording'

const router = useRouter()
const recordingStore = useRecordingStore()
const isOpen = ref(false)
const prompt = ref('')
const loading = ref(false)
const historyRef = ref<HTMLElement | null>(null)
const messages = ref<any[]>([])
const message = useMessage()

const handleSend = async () => {
  if (!prompt.value.trim() || loading.value) return
  
  const userText = prompt.value
  messages.value.push({ role: 'user', text: userText })
  prompt.value = ''
  loading.value = true
  
  await scrollToBottom()
  
  try {
    const res = await api.post('/ai/generate', { prompt: userText })
    messages.value.push({
      role: 'ai',
      text: res.data.message,
      steps: res.data.steps
    })
  } catch (err) {
    messages.value.push({
      role: 'ai',
      text: '抱歉，我现在无法处理您的请求，请检查后端 AI 配置。'
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const getActionType = (action: string) => {
  const map: any = {
    'goto': 'info',
    'click': 'primary',
    'fill': 'warning',
    'wait': 'default',
    'press': 'error',
    'hover': 'secondary',
    'select': 'success'
  }
  return map[action] || 'default'
}

const useSteps = (steps: any[]) => {
  console.log('AI useSteps triggered:', steps)
  isOpen.value = false
  
  try {
    // 1. Save to global store for late pickup
    recordingStore.setPendingSteps(steps)
    
    // 2. Broadcast event for immediate pickup if on Recording page
    window.dispatchEvent(new CustomEvent('ai-use-steps', { detail: steps }))
    
    message.success(`成功规划 ${steps.length} 个步骤，正在前往录制页面...`)
  } catch (err) {
    console.warn('Store or message provider failed, but continuing to navigate:', err)
  }
  
  // 3. Navigate
  router.push('/recording').catch(err => {
    console.error('Navigation failed:', err)
    message.error('无法自动跳转到录制页面，请手动点击侧边栏“录制”')
  })
}

const scrollToBottom = async () => {
  await nextTick()
  if (historyRef.value) {
    historyRef.value.scrollTop = historyRef.value.scrollHeight
  }
}

watch(isOpen, (val) => {
  if (val) nextTick(scrollToBottom)
})
</script>

<style scoped>
.ai-console {
  position: fixed;
  right: 0;
  top: 60px; /* 避开 Header */
  bottom: 0;
  z-index: 1000;
  display: flex;
  pointer-events: none;
}

.ai-trigger {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: auto;
  background: white;
  padding: 12px 8px;
  border-radius: 12px 0 0 12px;
  box-shadow: -4px 0 15px rgba(0,0,0,0.08);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--color-border);
  border-right: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1001;
}

.ai-trigger:hover {
  padding-right: 12px;
  color: var(--color-primary);
  background: #f8faff;
}

.trigger-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.trigger-label {
  font-weight: 600;
  font-size: 13px;
  line-height: 1.2;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ai-panel {
  pointer-events: auto;
  width: 360px;
  background: white;
  border-left: 1px solid var(--color-border);
  box-shadow: -10px 0 30px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  transform: translateX(100%);
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.ai-console.is-open .ai-panel {
  transform: translateX(0);
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid var(--color-divider);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 16px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fcfcfd;
}

.chat-history {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-view {
  text-align: center;
  padding: 40px 20px;
}

.welcome-icon { font-size: 48px; margin-bottom: 16px; }
.welcome-view h3 { color: #666; margin-bottom: 24px; }

.suggest-chips {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chip {
  background: white;
  border: 1px solid var(--color-divider);
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  color: #555;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.chip:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(79, 129, 255, 0.04);
}

.message-row { display: flex; width: 100%; }
.message-row.user { justify-content: flex-end; }
.message-row.ai { justify-content: flex-start; }

.message-bubble {
  max-width: 85%;
  padding: 12px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.5;
}

.user .message-bubble {
  background: var(--color-primary);
  color: white;
  border-bottom-right-radius: 4px;
}

.ai .message-bubble {
  background: white;
  border: 1px solid var(--color-divider);
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.03);
}

.loading-bubble { display: flex; align-items: center; gap: 8px; color: #888; }

.steps-preview {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-divider);
}

.steps-header { font-size: 11px; color: #999; text-transform: uppercase; margin-bottom: 8px; }

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-mini-card {
  background: #f3f5f9;
  padding: 6px 8px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.action-tag { min-width: 50px; text-align: center; }

.panel-footer {
  padding: 16px;
  border-top: 1px solid var(--color-divider);
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
</style>
