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
            <span>当前项目: {{ connectedProjectName || '加载中...' }}</span>
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
                <n-button type="primary" secondary block size="small" @click="useSteps(msg.steps, msg.sourcePrompt || '')" style="margin-top: 10px">💾 选择归属并保存</n-button>
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

    <n-modal v-model:show="showSaveModal">
      <n-card
        title="💾 保存 AI 用例"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        style="width: 520px; max-width: 90vw;"
      >
        <n-form label-placement="top">
          <n-form-item label="用例名称">
            <n-input v-model:value="saveForm.name" placeholder="请输入用例名称" />
          </n-form-item>
          <n-form-item label="归属项目">
            <n-select
              v-model:value="saveForm.projectId"
              :options="projectOptions"
              placeholder="请选择项目"
              @update:value="handleSaveProjectChange"
            />
          </n-form-item>
          <n-form-item label="归属模块">
            <n-select
              v-model:value="saveForm.moduleId"
              :options="moduleOptions"
              placeholder="请选择模块"
              :disabled="!saveForm.projectId"
            />
          </n-form-item>
          <n-form-item label="用例描述">
            <n-input v-model:value="saveForm.description" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" />
          </n-form-item>
        </n-form>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="showSaveModal = false">取消</n-button>
            <n-button type="primary" :loading="savingCase" @click="confirmSaveCase">确认保存</n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { NIcon, NButton, NInput, NSpin, NTag, NTabs, NTabPane, NSelect, useMessage, NModal, NCard, NForm, NFormItem } from 'naive-ui'
import { 
  SparklesOutline as SparklesIcon, 
  CloseOutline as CloseIcon,
  PlanetOutline as SmartIcon,
  PaperPlaneOutline as SendIcon
} from '@vicons/ionicons5'
import api from '@/api'
import { useAppStore } from '@/stores/app'
import { bindGeneratedStepsToKnownElements, loadAiContext } from '@/utils/aiContext'
import { ensureAICaseModule, generateCaseName, normalizeGeneratedSteps } from '@/utils/aiCaseFlow'

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
const projectOptions = ref<{ label: string; value: number }[]>([])
const moduleOptions = ref<{ label: string; value: number }[]>([])
const showSaveModal = ref(false)
const savingCase = ref(false)
const pendingSaveSteps = ref<any[]>([])
const saveForm = ref({
  name: '',
  description: '',
  projectId: null as number | null,
  moduleId: null as number | null
})

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
      steps: [],
      sourcePrompt: userText
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
              if (Array.isArray(item.final_steps)) {
                currentMsg.steps = mergeAssistantSteps(currentMsg.steps || [], item.final_steps)
              }
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

const mergeAssistantSteps = (streamedSteps: any[], finalSteps: any[]) => {
  const merged = [...(streamedSteps || [])]
  for (const step of finalSteps || []) {
    const exists = merged.some((item) => item.action === step.action && item.target === step.target && item.value === step.value)
    if (!exists) {
      merged.push(step)
    }
  }
  return merged
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

const buildCaseName = (sourcePrompt: string, steps: any[]) => {
  const promptName = sourcePrompt.trim().replace(/\s+/g, ' ')
  if (promptName) return promptName.slice(0, 60)
  const firstMeaningfulStep = steps.find((step) => step.description || step.target || step.action)
  if (!firstMeaningfulStep) return 'AI生成用例'
  return String(firstMeaningfulStep.description || firstMeaningfulStep.target || firstMeaningfulStep.action).slice(0, 60)
}

const normalizeStepsForCase = (steps: any[]) => {
  return steps.map((step: any) => {
    const isWait = step.action === 'wait'
    const isWaitForSelector = step.action === 'wait_for_selector'
    const waitMs = (isWait || isWaitForSelector)
      ? (parseDurationToMs(step.wait_ms ?? step.value) ?? (isWait ? 1000 : 8000))
      : null

    return {
      action: step.action,
      target: step.target || step.selector || '',
      selector: step.target || step.selector || '',
      value: (isWait || isWaitForSelector)
        ? String(waitMs)
        : (step.value || ''),
      wait_ms: waitMs,
      description: step.description || '',
      page_id: step.page_id || null,
      element_id: step.element_id || null,
      locator_chain: step.locator_chain || null,
      variable_name: step.variable_name || ''
    }
}
}

const fetchProjects = async () => {
  const res = await api.get('/projects/')
  projectOptions.value = (res.data || []).map((project: any) => ({
    label: project.name,
    value: project.id
  }))
}

const fetchModules = async (projectId: number | null) => {
  if (!projectId) {
    moduleOptions.value = []
    saveForm.value.moduleId = null
    return
  }

  const res = await api.get(`/modules/?project_id=${projectId}`)
  moduleOptions.value = (res.data || []).map((module: any) => ({
    label: module.name,
    value: module.id
  }))

  if (!moduleOptions.value.find((module) => module.value === saveForm.value.moduleId)) {
    saveForm.value.moduleId = moduleOptions.value[0]?.value ?? null
  }
}

const handleSaveProjectChange = async (projectId: number | null) => {
  saveForm.value.projectId = projectId
  saveForm.value.moduleId = null
  await fetchModules(projectId)
}

const useSteps = async (steps: any[], sourcePrompt: string) => {
  if (!steps?.length) {
    message.warning('未生成有效步骤，无法保存用例')
    return
  }

  try {
    pendingSaveSteps.value = normalizeStepsForCase(steps)
    saveForm.value = {
      name: buildCaseName(sourcePrompt, steps),
      description: sourcePrompt.trim() || '由 AI 助手自动生成',
      projectId: appStore.selectedProjectId,
      moduleId: appStore.selectedModuleId
    }

    await fetchProjects()
    await fetchModules(saveForm.value.projectId)
    showSaveModal.value = true
  } catch (err: any) {
    message.error(err?.response?.data?.detail || err?.message || '加载保存选项失败')
  }
}

const confirmSaveCase = async () => {
  if (!saveForm.value.name.trim()) {
    message.warning('请输入用例名称')
    return
  }
  if (!saveForm.value.projectId) {
    message.warning('请选择归属项目')
    return
  }
  if (!saveForm.value.moduleId) {
    message.warning('请选择归属模块')
    return
  }
  if (!pendingSaveSteps.value.length) {
    message.warning('没有可保存的步骤')
    return
  }

  savingCase.value = true
  try {
    await api.post('/cases/', {
      name: saveForm.value.name.trim(),
      description: saveForm.value.description.trim(),
      priority: 'P1',
      module_id: saveForm.value.moduleId,
      steps: pendingSaveSteps.value
    })
    showSaveModal.value = false
    isOpen.value = false
    pendingSaveSteps.value = []
    message.success('AI 用例已保存到用例库')
  } catch (err: any) {
    message.error(err?.response?.data?.detail || err?.message || '保存用例失败')
  } finally {
    savingCase.value = false
  }
}

const fetchModels = async () => {
  try {
    const res = await api.get('/ai-models/')
    aiModelOptions.value = res.data.map((m: any) => ({ label: m.name, value: String(m.id) }))
    if (res.data.length > 0) selectedAIModel.value = String(res.data[0].id)
  } catch (e) {}
}

onMounted(async () => {
  await fetchModels()
  await fetchProjects()
})
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
