export interface GeneratedStep {
  action: string
  target?: string | null
  selector?: string | null
  value?: string | null
  wait_ms?: number | string | null
  locator_chain?: Record<string, any> | null
  locator_type?: string | null
  description?: string | null
  variable_name?: string | null
  page_id?: number | null
  element_id?: number | null
  [key: string]: any
}

export interface ModuleSummary {
  id: number
  name: string
  project_id: number
}

export interface CreateModulePayload {
  name: string
  project_id: number
  description?: string
}

export const DEFAULT_AI_MODULE_NAME = 'AI 生成用例'

function parseDurationToMs(raw: any): number | null {
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

function mapAction(action: string): string {
  const a = String(action || '').toLowerCase()
  if (a.includes('wait_for_selector') || a.includes('wait for selector') || a.includes('等待元素')) return 'wait_for_selector'
  if (a.includes('assert_visible') || a.includes('visible') || a.includes('可见')) return 'assert_visible'
  if (a.includes('assert') || a.includes('verify') || a.includes('check') || a.includes('断言') || a.includes('验证') || a.includes('检查')) return 'assert_text'
  if (a.includes('hover') || a.includes('悬停')) return 'hover'
  if (a.includes('select') || a.includes('选择')) return 'select'
  if (a.includes('press') || a.includes('按键')) return 'press'
  if (a.includes('click') || a.includes('点击')) return 'click'
  if (a.includes('fill') || a.includes('type') || a.includes('input') || a.includes('输入') || a.includes('填写')) return 'fill'
  if (a.includes('goto') || a.includes('visit') || a.includes('open') || a.includes('navigate') || a.includes('跳转') || a.includes('访问') || a.includes('打开')) return 'goto'
  if (a.includes('wait') || a.includes('sleep') || a.includes('等待')) return 'wait'
  if (a.includes('screenshot') || a.includes('截图')) return 'screenshot'
  if (a.includes('get_text') || a.includes('text_content') || a.includes('提取文本')) return 'get_text'
  if (a.includes('get_attribute') || a.includes('extract_attr') || a.includes('提取属性')) return 'get_attribute'
  if (a.includes('set_variable') || a.includes('设置变量')) return 'set_variable'
  return a || 'click'
}

function buildDefaultDescription(action: string, target: string, value: string, waitMs: number | null): string {
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

export function normalizeGeneratedSteps<T extends GeneratedStep>(steps: T[]): T[] {
  return steps.map((step) => {
    const action = mapAction(step.action)
    let value = String(step.value || '').trim()
    let target = String(step.target || step.selector || '').trim()

    if (action === 'goto' && !value && target) {
      value = target
      target = ''
    }

    const waitMs = action === 'wait' ? (parseDurationToMs(step.wait_ms ?? value) ?? 1000) : null
    if (action === 'wait') value = String(waitMs)

    const waitForSelectorMs = action === 'wait_for_selector'
      ? (parseDurationToMs(step.wait_ms ?? value) ?? 8000)
      : null
    if (action === 'wait_for_selector') value = String(waitForSelectorMs)

    const finalWaitMs = action === 'wait' ? waitMs : (action === 'wait_for_selector' ? waitForSelectorMs : null)

    return {
      ...step,
      action,
      target,
      selector: target,
      value,
      wait_ms: finalWaitMs,
      description: String(step.description || '').trim() || buildDefaultDescription(action, target, value, finalWaitMs),
    }
  }) as T[]
}

export async function ensureAICaseModule(options: {
  projectId: number
  fetchModules: (projectId: number) => Promise<ModuleSummary[]>
  createModule: (payload: CreateModulePayload) => Promise<ModuleSummary>
}): Promise<number> {
  const modules = await options.fetchModules(options.projectId)
  const existing = modules.find((item) => item.name === DEFAULT_AI_MODULE_NAME)
  if (existing) return existing.id

  const created = await options.createModule({
    project_id: options.projectId,
    name: DEFAULT_AI_MODULE_NAME,
    description: 'AI 助手自动生成并沉淀的测试用例默认模块'
  })
  return created.id
}

export function generateCaseName(options: { prompt: string; steps: GeneratedStep[] }): string {
  const prompt = String(options.prompt || '').trim().replace(/\s+/g, ' ')
  if (prompt) {
    return prompt.length > 40 ? `${prompt.slice(0, 40).trim()}...` : prompt
  }

  const firstMeaningful = options.steps.find((step) => String(step.description || '').trim())
  if (firstMeaningful?.description) {
    return String(firstMeaningful.description).trim()
  }

  return `AI生成用例-${new Date().toISOString().slice(0, 16).replace('T', ' ')}`
}
