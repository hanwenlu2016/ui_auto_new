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
              
              <!-- Generated Steps Preview (Support both Array and Scenario Object formats) -->
              <div v-if="(msg.steps && msg.steps.length > 0) || (msg.scenarios && Object.keys(msg.scenarios).length > 0)" class="steps-preview">
                
                <!-- If it's the new scenario format -->
                <div v-if="msg.scenarios">
                  <n-tabs type="segment" animated>
                    <n-tab-pane name="happy" tab="常规路径" v-if="msg.scenarios.happy_path && msg.scenarios.happy_path.length > 0">
                      <div class="steps-list">
                        <div v-for="(step, si) in msg.scenarios.happy_path" :key="si" class="step-mini-card">
                          <div class="step-main">
                            <n-tag :type="getActionType(step.action)" size="small" class="action-tag">{{ mapActionIcon(step.action) }}</n-tag>
                            <span class="step-desc">{{ step.description || step.target }}</span>
                          </div>
                          <div class="step-actions">
                            <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_up')" title="赞同此步骤">👍</n-button>
                            <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_down')" title="此步骤有误">👎</n-button>
                          </div>
                        </div>
                      </div>
                      <n-button type="primary" secondary block size="small" @click="useSteps(msg.scenarios.happy_path)" style="margin-top: 12px">🚀 导入常规路径</n-button>
                    </n-tab-pane>

                    <n-tab-pane name="boundary" tab="边界测试" v-if="msg.scenarios.boundary && msg.scenarios.boundary.length > 0">
                       <div class="steps-list">
                        <div v-for="(step, si) in msg.scenarios.boundary" :key="si" class="step-mini-card">
                           <div class="step-main">
                            <n-tag :type="getActionType(step.action)" size="small" class="action-tag">{{ mapActionIcon(step.action) }}</n-tag>
                            <span class="step-desc">{{ step.description || step.target }}</span>
                          </div>
                          <div class="step-actions">
                            <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_up')">👍</n-button>
                            <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_down')">👎</n-button>
                          </div>
                        </div>
                      </div>
                      <n-button type="info" secondary block size="small" @click="useSteps(msg.scenarios.boundary)" style="margin-top: 12px">🧪 导入边界测试</n-button>
                    </n-tab-pane>

                    <n-tab-pane name="negative" tab="异常测试" v-if="msg.scenarios.negative && msg.scenarios.negative.length > 0">
                       <div class="steps-list">
                        <div v-for="(step, si) in msg.scenarios.negative" :key="si" class="step-mini-card">
                           <div class="step-main">
                            <n-tag :type="getActionType(step.action)" size="small" class="action-tag">{{ mapActionIcon(step.action) }}</n-tag>
                            <span class="step-desc">{{ step.description || step.target }}</span>
                           </div>
                           <div class="step-actions">
                            <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_up')">👍</n-button>
                            <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_down')">👎</n-button>
                          </div>
                        </div>
                      </div>
                      <n-button type="error" secondary block size="small" @click="useSteps(msg.scenarios.negative)" style="margin-top: 12px">⚠️ 导入异常测试</n-button>
                    </n-tab-pane>
                  </n-tabs>
                </div>

                <!-- Fallback for array format (old generate_steps) -->
                <div v-else-if="msg.steps && Array.isArray(msg.steps) && msg.steps.length > 0">
                  <div class="steps-header">规划了 {{ msg.steps.length }} 个自动化动作</div>
                  <div class="steps-list">
                    <div v-for="(step, si) in msg.steps" :key="si" class="step-mini-card">
                      <div class="step-main">
                        <n-tag :type="getActionType(step.action)" size="small" class="action-tag">
                          {{ mapActionIcon(step.action) }}
                        </n-tag>
                        <span class="step-desc">{{ step.description || step.target }}</span>
                      </div>
                      <div class="step-actions">
                         <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_up')" title="赞同此步骤">👍</n-button>
                         <n-button text circle @click="submitFeedback(msg, step, si, 'thumbs_down')" title="此步骤有误">👎</n-button>
                      </div>
                    </div>
                  </div>
                  <n-button type="primary" secondary block size="small" @click="useSteps(msg.steps)" style="margin-top: 12px">
                    🚀 立即导入步骤并开始
                  </n-button>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="loading" class="message-row ai">
            <div class="message-bubble loading-bubble">
              <n-spin size="small" />
              <span>{{ agentMode ? 'Agent 正在执行浏览器操作...' : 'AI 正在思考...' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="panel-footer">
        <div class="footer-toolbar">
          <n-select
            v-model:value="selectedAIModel"
            :options="aiModelOptions"
            size="small"
            style="width: 140px"
            placeholder="AI 引擎"
          />
          <div class="mode-toggle">
            <span class="mode-label" :class="{ active: !agentMode }">快速</span>
            <n-switch v-model:value="agentMode" size="small" />
            <span class="mode-label" :class="{ active: agentMode }">精准</span>
          </div>
        </div>
        <div class="input-row">
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
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NButton, NInput, NSpin, NTag, NTabs, NTabPane, NSelect, NSwitch, useMessage } from 'naive-ui'
import { 
  SparklesOutline as SparklesIcon, 
  CloseOutline as CloseIcon,
  PlanetOutline as SmartIcon,
  PaperPlaneOutline as SendIcon
} from '@vicons/ionicons5'
import api from '@/api'
import { useRecordingStore } from '@/stores/recording'
import { useAppStore } from '@/stores/app'
import { bindGeneratedStepsToKnownElements, loadAiContext } from '@/utils/aiContext'

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

const handleSend = async () => {
  if (!prompt.value.trim() || loading.value) return
  
  const userText = prompt.value
  messages.value.push({ role: 'user', text: userText })
  prompt.value = ''
  loading.value = true
  
  await scrollToBottom()
  
  try {
    if (agentMode.value) {
      // 精准执行模式: 调用 browser-use Agent (流式传输进度)
      const msgObj = {
        role: 'ai',
        text: 'Agent 正在启动浏览器...',
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
            max_steps: 20,
            use_vision: false
          })
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || '请求失败')
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('流读取器不可用')

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
                // 标准化步骤属性，并确保数组更新是响应式的
                const rawStep = item.data
                const formattedStep = {
                  action: rawStep.action,
                  target: rawStep.target || '',
                  selector: rawStep.target || '',
                  value: rawStep.value || '',
                  description: rawStep.description || `${rawStep.action} ${rawStep.target || ''}`.trim()
                }
                
                currentMsg.steps = [...(currentMsg.steps || []), formattedStep]
                currentMsg.text = `Agent 正在执行第 ${item.step_number} 步: ${formattedStep.action}...`
              } else if (item.type === 'done') {
                if (item.final_steps) {
                  currentMsg.steps = item.final_steps.map((s: any) => ({
                    action: s.action,
                    target: s.target || '',
                    selector: s.target || '',
                    value: s.value || '',
                    description: s.description
                  }))
                }
                currentMsg.text = `Agent 执行完成！共捕获 ${item.total_steps} 个自动化步骤，点击下方按钮导入到用例。`
              }
 else if (item.type === 'error') {
                currentMsg.text = `执行遇到问题: ${item.message}`
              }
              
              // 关键：替换整个对象以确保 Vue 触发响应式循环
              messages.value[messageIndex] = currentMsg
              await scrollToBottom()
            } catch (e) {
              console.error('Stream parse error:', e, line)
            }
          }
        }
      } catch (err: any) {
        console.error('[Agent Stream Error]:', err)
        messages.value[messageIndex].text = `抱歉，Agent 执行失败: ${err.message || '网络连接超时'}`
      }
    } else {
      // 快速生成模式: 调用现有 AIService
      const aiContext = await loadAiContext(appStore.selectedProjectId, appStore.selectedModuleId)
      const res = await api.post('ai/generate', { 
        prompt: userText,
        model_id: selectedAIModel.value,
        project_id: appStore.selectedProjectId,
        business_rules: aiContext.businessRules || undefined
      })
      const binding = bindGeneratedStepsToKnownElements(res.data.steps || [], aiContext.knownElements)
      messages.value.push({
        role: 'ai',
        text: res.data.message,
        steps: binding.steps
      })
      if (binding.boundCount > 0) {
        message.info(`AI 结果中有 ${binding.boundCount} 个步骤已绑定到项目元素库`)
      }
      if (binding.unboundInteractiveCount > 0) {
        message.warning(`仍有 ${binding.unboundInteractiveCount} 个交互步骤未绑定到项目元素库`)
      }
    }
  } catch (err: any) {
    console.error('[AI Chat Error]:', err)
    const detail = err.response?.data?.detail || err.message || '未知错误'
    messages.value.push({
      role: 'ai',
      text: `抱歉，请求失败: ${detail}。请检查后端输出或配置。`
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
    'select': 'success',
    'scroll': 'info',
    'get_text': 'success',
    'assert_text': 'success'
  }
  return map[action] || 'default'
}

const mapAction = (action: string) => {
  const a = (action || '').toLowerCase()
  if (a.includes('goto')) return 'goto'
  if (a.includes('click')) return 'click'
  if (a.includes('input') || a.includes('fill')) return 'fill'
  if (a.includes('wait') || a.includes('sleep')) return 'wait'
  if (a.includes('scroll')) return 'scroll'
  if (a.includes('extract') || a.includes('get_text')) return 'get_text'
  if (a.includes('hover')) return 'hover'
  if (a.includes('select')) return 'select'
  if (a.includes('press')) return 'press'
  if (a.includes('assert') || a.includes('verify')) return 'assert_text'
  return a
}

const mapActionIcon = (action: string) => {
  const a = mapAction(action)
  switch (a) {
    case 'goto': return '🔗 跳转'
    case 'click': return '🖱️ 点击'
    case 'fill': return '⌨️ 输入'
    case 'wait': return '⌛ 等待'
    case 'scroll': return '📜 滚动'
    case 'get_text': return '📋 提取'
    case 'hover': return '🖱️ 悬停'
    case 'select': return '🔽 选择'
    case 'press': return '⌨️ 按键'
    case 'assert_text': return '✅ 断言'
    default: return '⚡ ' + action
  }
}

const useSteps = (steps: any[]) => {
  console.log('AI useSteps triggered:', steps)
  isOpen.value = false
  
  // 保持原有转换逻辑以确保最终导入到步骤编辑器的数据是正确的
  const convertAction = (action: string) => {
    const a = (action || '').toLowerCase()
    if (a.includes('wait_for_selector') || a.includes('wait for selector') || a.includes('等待元素')) return 'wait_for_selector'
    if (a.includes('assert_visible') || a.includes('visible') || a.includes('可见')) return 'assert_visible'
    if (a.includes('click') || a.includes('点击')) return 'click'
    if (a.includes('press') || a.includes('按键')) return 'press'
    if (a.includes('fill') || a.includes('type') || a.includes('input') || a.includes('输入') || a.includes('填写')) return 'fill'
    if (a.includes('select') || a.includes('选择')) return 'select'
    if (a.includes('hover') || a.includes('悬停')) return 'hover'
    if (a.includes('goto') || a.includes('visit') || a.includes('open') || a.includes('navigate') || a.includes('跳转') || a.includes('访问') || a.includes('打开')) return 'goto'
    if (a.includes('assert') || a.includes('verify') || a.includes('check') || a.includes('断言') || a.includes('验证') || a.includes('检查')) return 'assert_text'
    if (a.includes('wait') || a.includes('sleep') || a.includes('等待')) return 'wait'
    if (a.includes('screenshot') || a.includes('截图')) return 'screenshot'
    if (a.includes('get_text') || a.includes('get_element_text') || a.includes('提取文本')) return 'get_text'
    if (a.includes('get_attribute') || a.includes('extract_attr') || a.includes('提取属性')) return 'get_attribute'
    if (a.includes('set_variable') || a.includes('设置变量')) return 'set_variable'
    return a
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

  const buildDefaultDescription = (action: string, target: string, value: string, waitMs: number | null) => {
    if (action === 'goto') return `访问页面 ${value || target || ''}`.trim()
    if (action === 'wait') return `等待 ${(waitMs ?? 1000) / 1000}s`
    if (action === 'wait_for_selector') return `等待元素出现: ${target || '目标元素'} (超时 ${(waitMs ?? 8000) / 1000}s)`
    if (action === 'click') return `点击 ${target || '目标元素'}`
    if (action === 'fill') return `输入内容到 ${target || '输入框'}`
    if (action === 'assert_text') return `断言 ${target || '元素'} 包含文本 ${value || ''}`.trim()
    if (action === 'assert_visible') return `断言元素可见: ${target || '目标元素'}`
    if (action === 'select') return `选择 ${value || ''} 于 ${target || '下拉框'}`.trim()
    if (action === 'press') return `在 ${target || '目标元素'} 按键 ${value || ''}`.trim()
    if (action === 'screenshot') return '截图'
    return '执行动作'
  }

  const normalizedSteps = steps.map(s => {
    const action = convertAction(s.action)
    let val = String(s.value || '').trim()
    let tar = s.target || s.selector || ''
    
    if (action === 'goto' && !val && tar) {
      val = tar
      tar = ''
    }

    const waitMs = action === 'wait' ? (parseDurationToMs(s.wait_ms ?? val) ?? 1000) : null
    if (action === 'wait') {
      val = String(waitMs)
    }
    const waitForSelectorMs = action === 'wait_for_selector' ? (parseDurationToMs(s.wait_ms ?? val) ?? 8000) : null
    if (action === 'wait_for_selector') {
      val = String(waitForSelectorMs)
    }
    const finalWaitMs = action === 'wait' ? waitMs : (action === 'wait_for_selector' ? waitForSelectorMs : null)
    
    return {
      ...s,
      action: action,
      target: String(tar || '').trim(),
      selector: String(tar || '').trim(),
      value: String(val || '').trim(),
      wait_ms: finalWaitMs,
      description: (s.description || '').trim() || buildDefaultDescription(action, String(tar || '').trim(), String(val || '').trim(), finalWaitMs)
    }
  })

  try {
    // 1. Save to global store for late pickup
    recordingStore.setPendingSteps(normalizedSteps)
    
    // 2. Broadcast event for immediate pickup if on Recording page
    window.dispatchEvent(new CustomEvent('ai-use-steps', { detail: normalizedSteps }))
    
    message.success(`成功导入 ${normalizedSteps.length} 个步骤，请前往录制页面查看。`)
  } catch (err) {
    console.warn('Store or message provider failed, but continuing to navigate:', err)
  }
  
  // 3. Navigate
  router.push('/recording').catch(err => {
    console.error('Navigation failed:', err)
    message.error('无法自动跳转到录制页面，请手动点击侧边栏“录制”')
  })
}

const submitFeedback = async (_msg: any, step: any, index: number | string, type: string) => {
  try {
    // 使用相对路径 'ai/feedback' 确保拼接 baseURL
    await api.post('ai/feedback', {
      project_id: appStore.selectedProjectId,
      step_index: Number(index),
      feedback_type: type,
      original_step: step
    })
    message.success(type === 'thumbs_up' ? '感谢赞同！已加入 AI 记忆池。' : '感谢反馈！AI 将在未来改进此类选择器。')
  } catch (err) {
    message.error('反馈送达失败')
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (historyRef.value) {
    historyRef.value.scrollTop = historyRef.value.scrollHeight
  }
}

const fetchAIModels = async () => {
  try {
    const res = await api.get('/ai-models/')
    const activeModels = res.data.filter((m: any) => m.is_active)
    aiModelOptions.value = activeModels.map((m: any) => ({
      label: m.is_default ? `${m.name} (默认)` : m.name,
      value: String(m.id)
    }))
    
    // Set default model
    const defaultModel = activeModels.find((m: any) => m.is_active && m.is_default)
    if (defaultModel) {
      selectedAIModel.value = String(defaultModel.id)
    } else if (activeModels.length > 0) {
      selectedAIModel.value = String(activeModels[0].id)
    }
  } catch (error) {
    console.error('Failed to fetch AI models', error)
  }
}

import { onMounted } from 'vue'
onMounted(fetchAIModels)

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
  padding: 12px 16px;
  border-top: 1px solid var(--color-divider);
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: white;
}

.footer-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.mode-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-label {
  font-size: 11px;
  color: #999;
  transition: color 0.2s;
}

.mode-label.active {
  color: var(--color-primary);
  font-weight: 600;
}

.input-row {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
</style>
