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

              <!-- Discovery Results (AI Page Modeling) -->
              <div v-if="msg.discoveredElements && msg.discoveredElements.length > 0" class="discovery-box">
                <div class="discovery-header">
                  <span class="title">🔍 发现 {{ msg.discoveredElements.length }} 个页面元素</span>
                  <n-button size="tiny" tertiary type="primary" @click="toggleSelectAll(msg)">全选</n-button>
                </div>
                <div class="discovery-list">
                  <div v-for="(el, ei) in msg.discoveredElements" :key="ei" class="discovery-item">
                    <n-checkbox v-model:checked="el.selected" />
                    <div class="item-info">
                      <div class="name-row">
                        <span class="name">{{ el.name }}</span>
                        <n-tag size="tiny" round :type="getActionType(el.type)">{{ el.type }}</n-tag>
                      </div>
                      <div class="selector">{{ el.locator_value }}</div>
                    </div>
                  </div>
                </div>
                <n-button 
                  type="success" 
                  block 
                  size="small" 
                  :loading="msg.syncing"
                  @click="syncSelectedElements(msg)"
                  style="margin-top: 12px"
                >
                  📥 同步到项目资产库
                </n-button>
              </div>
            </div>
          </div>
          
          <div v-if="loading" class="message-block ai">
            <div class="message-content loading-state">
              <n-spin size="small" />
              <span>{{ agentMode ? 'Agent 正在执行...' : 'AI 正在思考...' }}</span>
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
            <div class="mode-switch">
              <span class="label" :class="{ active: !agentMode }" @click="agentMode = false">快速脑暴</span>
              <n-switch v-model:value="agentMode" size="small" />
              <span class="label" :class="{ active: agentMode }" @click="agentMode = true">精准执行</span>
            </div>
            <n-button 
              size="small" 
              type="primary" 
              quaternary 
              @click="handleScan"
              :loading="scanning"
            >
              <template #icon><n-icon><search-icon /></n-icon></template>
              智能分析页面
            </n-button>
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
import { NIcon, NButton, NInput, NSpin, NTag, NSelect, NSwitch, useMessage, NModal } from 'naive-ui'
import { 
  SparklesOutline as SparklesIcon, 
  PlanetOutline as SmartIcon,
  PaperPlaneOutline as SendIcon,
  SearchOutline as SearchIcon
} from '@vicons/ionicons5'
import api from '@/api'
import { useRecordingStore } from '@/stores/recording'
import { useAppStore } from '@/stores/app'
import { bindGeneratedStepsToKnownElements, loadAiContext, loadLiveAiRuntimeContext } from '@/utils/aiContext'

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
const agentMode = ref(false)
const scanning = ref(false)
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

watch(() => appStore.selectedProjectId, fetchProjectName, { immediate: true })

// Discovery logic
const handleScan = async () => {
  scanning.value = true
  try {
    const liveContext = await loadLiveAiRuntimeContext()
    if (!liveContext.available) {
      message.warning('未检测到录制中的被测页面，请先在录制页面启动浏览器后再分析。')
      return
    }

    const res = await api.post('ai/discover', {
      dom_snapshot: liveContext.domSnapshot,
      model_id: selectedAIModel.value
    })
    messages.value.push({
      role: 'ai',
      text: `${res.data.message}${liveContext.title ? ` 当前页面: ${liveContext.title}` : ''}`,
      discoveredElements: res.data.elements.map((el: any) => ({ ...el, selected: true })),
      syncing: false
    })
  } catch (e) {
    message.error('页面分析失败，请稍后重试')
  } finally {
    scanning.value = false
    scrollToBottom()
  }
}

const toggleSelectAll = (msg: any) => {
  const allSelected = msg.discoveredElements.every((el: any) => el.selected)
  msg.discoveredElements.forEach((el: any) => el.selected = !allSelected)
}

const syncSelectedElements = async (msg: any) => {
  const selected = msg.discoveredElements.filter((el: any) => el.selected)
  if (selected.length === 0) {
    message.warning('请先勾选要同步的元素')
    return
  }
  
  if (!appStore.selectedProjectId) {
    message.warning('请先选择一个关联项目')
    return
  }

  msg.syncing = true
  try {
    // 1. Ensure we have a general 'AI_Discovery' Page for this module/project
    // For simplicity, we'll save directly into the current selected module or prompt
    // Let's assume we use the first page of the project or create an 'Auto-Discovered' page
    
    // FETCH PAGES
    const pagesRes = await api.get(`/pages/?project_id=${appStore.selectedProjectId}`)
    let targetPageId = pagesRes.data?.[0]?.id

    if (!targetPageId) {
      // Create a default page if none exists
      const newPageRes = await api.post('/pages/', {
        name: 'AI 自动发现页面',
        project_id: appStore.selectedProjectId,
        module_id: appStore.selectedModuleId
      })
      targetPageId = newPageRes.data.id
    }

    // 2. Batch save elements
    for (const el of selected) {
      await api.post('/elements/', {
        name: el.name,
        description: el.description,
        page_id: targetPageId,
        locator_type: el.locator_type || 'xpath',
        locator_value: el.locator_value,
        metadata_json: { discovered: true, type: el.type }
      })
    }
    
    message.success(`成功同步 ${selected.length} 个元素到资产库！`)
    msg.discoveredElements = [] // Clear after success
  } catch (e) {
    message.error('同步失败，请检查网络或项目配置')
  } finally {
    msg.syncing = false
  }
}

const handleSend = async () => {
  if (!prompt.value.trim() || loading.value) return
  
  const userText = prompt.value
  messages.value.push({ role: 'user', text: userText })
  prompt.value = ''
  loading.value = true
  
  await scrollToBottom()
  
  try {
    if (agentMode.value) {
      const msgObj = {
        role: 'ai',
        text: 'Agent 正在启动...',
        steps: [],
        isAgent: true
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
            max_steps: 20
          })
        })

        if (!response.ok) throw new Error('流式请求失败')
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
                currentMsg.text = `任务执行完毕，共录制 ${item.total_steps} 个步骤。`
              }
              messages.value[messageIndex] = currentMsg
              await scrollToBottom()
            } catch (e) {}
          }
        }
      } catch (err: any) {
        messages.value[messageIndex].text = `执行失败: ${err.message}`
      }
    } else {
      const aiContext = await loadAiContext(appStore.selectedProjectId, appStore.selectedModuleId)
      const liveContext = await loadLiveAiRuntimeContext()
      const businessRules = [aiContext.businessRules, liveContext.contextHint].filter(Boolean).join('\n')
      const res = await api.post('ai/generate', { 
        prompt: userText,
        model_id: selectedAIModel.value,
        project_id: appStore.selectedProjectId,
        business_rules: businessRules || undefined,
        dom_snapshot: liveContext.available ? liveContext.domSnapshot : undefined,
        screenshot_description: liveContext.available
          ? `Active AUT page title: ${liveContext.title || 'Unknown'}; URL: ${liveContext.url || 'Unknown'}`
          : undefined
      })
      const binding = bindGeneratedStepsToKnownElements(res.data.steps || [], aiContext.knownElements)
      messages.value.push({
        role: 'ai',
        text: liveContext.available ? `${res.data.message} (已注入真实页面上下文)` : res.data.message,
        steps: binding.steps
      })
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

const scrollToBottom = async () => {
  await nextTick()
  if (historyRef.value) historyRef.value.scrollTop = historyRef.value.scrollHeight
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

.mode-switch {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-switch .label {
  font-size: 13px;
  color: #a0aec0;
  cursor: pointer;
  user-select: none;
  transition: all 0.3s;
}

.mode-switch .label.active {
  color: var(--color-primary);
  font-weight: 700;
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

/* Discovery UI */
.discovery-box {
  margin-top: 15px;
  background: white;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}

.discovery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e2e8f0;
}

.discovery-header .title {
  font-weight: 700;
  color: #334155;
  font-size: 13px;
}

.discovery-list {
  max-height: 250px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.discovery-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.discovery-item:hover {
  border-color: var(--color-primary);
  background: #f1f5f9;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-row .name {
  font-weight: 600;
  font-size: 13px;
  color: #1e293b;
}

.item-info .selector {
  font-family: monospace;
  font-size: 11px;
  color: #64748b;
  word-break: break-all;
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
