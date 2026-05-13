import api from '@/api'

export interface AiProject {
  id: number
  name: string
  base_url?: string | null
  description?: string | null
}

export interface AiPage {
  id: number
  module_id: number
  name: string
  description?: string | null
}

export interface AiElement {
  id: number
  page_id: number
  name: string
  description?: string | null
  locator_type?: string | null
  locator_value: string
  metadata_json?: Record<string, any> | null
  page_name?: string
}

export interface AiContextBundle {
  project: AiProject | null
  pages: AiPage[]
  knownElements: AiElement[]
  businessRules: string
}

export interface LiveAiRuntimeContext {
  available: boolean
  source: string
  url: string | null
  title: string | null
  domSnapshot: string
  contextHint: string
}

function normalizeSelector(selector: string | null | undefined): string {
  return String(selector || '')
    .trim()
    .replace(/:visible\b/gi, '')
    .replace(/\s+/g, ' ')
}

function normalizeMatchText(text: string | null | undefined): string {
  return String(text || '')
    .trim()
    .toLowerCase()
    .replace(/[\[\](){}<>"'`]/g, ' ')
    .replace(/[_:/\\|,+.=*-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function compactMatchText(text: string | null | undefined): string {
  return normalizeMatchText(text).replace(/[\W_]+/g, '')
}

function tokenizeMatchText(text: string | null | undefined): string[] {
  return normalizeMatchText(text)
    .split(/\s+/)
    .filter((token) => token.length >= 2)
}

function getElementSelectorCandidates(element: AiElement): string[] {
  const metadata = element.metadata_json || {}
  const recommendedChain = metadata.ai_recommended_locator_chain || {}
  const rawSelectors = [
    element.locator_value,
    metadata.last_healed_selector,
    ...(Array.isArray(metadata.human_verified_selectors) ? metadata.human_verified_selectors : []),
    ...(Array.isArray(metadata.healing_selectors) ? metadata.healing_selectors : []),
    recommendedChain.primary,
    recommendedChain.fallback_1,
    recommendedChain.fallback_2,
    recommendedChain.fallback_3
  ]

  return Array.from(
    new Set(
      rawSelectors
        .map((raw) => normalizeSelector(raw))
        .filter(Boolean)
    )
  )
}

function getElementAliases(element: AiElement): string[] {
  const aliases = [
    element.name,
    element.description,
    element.page_name,
    `${element.page_name || ''} ${element.name || ''}`,
    `${element.page_name || ''} ${element.description || ''}`
  ]

  return Array.from(
    new Set(
      aliases
        .map((value) => normalizeMatchText(value))
        .filter(Boolean)
    )
  )
}

function scoreElementMatch(step: Record<string, any>, element: AiElement): number {
  const stepSelectors = new Set(getStepSelectorCandidates(step))
  const elementSelectors = new Set(getElementSelectorCandidates(element))
  for (const selector of stepSelectors) {
    if (elementSelectors.has(selector)) {
      return 120
    }
  }

  const action = String(step.action || '').toLowerCase()
  const stepText = [step.target, step.selector, step.description, step.value].filter(Boolean).join(' ')
  const normalizedStepText = normalizeMatchText(stepText)
  const compactStepText = compactMatchText(stepText)
  const stepTokens = new Set(tokenizeMatchText(stepText))
  let score = 0

  for (const alias of getElementAliases(element)) {
    const compactAlias = compactMatchText(alias)
    const aliasTokens = new Set(tokenizeMatchText(alias))

    if (normalizedStepText === alias) {
      score = Math.max(score, 95)
    } else if (compactAlias && compactAlias === compactStepText) {
      score = Math.max(score, 92)
    } else if (compactAlias && compactStepText.includes(compactAlias)) {
      score = Math.max(score, 84)
    } else if (compactStepText && compactAlias.includes(compactStepText)) {
      score = Math.max(score, 78)
    }

    const overlapCount = Array.from(stepTokens).filter((token) => aliasTokens.has(token)).length
    if (overlapCount > 0) {
      score = Math.max(score, 55 + overlapCount * 8)
    }
  }

  const elementType = String((element as any).type || element.locator_type || '').toLowerCase()
  if (['fill', 'select'].includes(action) && ['input', 'select', 'textarea'].includes(elementType)) {
    score += 6
  }
  if (['click', 'hover', 'press'].includes(action) && ['button', 'link', 'other', 'css'].includes(elementType)) {
    score += 4
  }

  return score
}

function buildBusinessRules(project: AiProject | null, pages: AiPage[], elements: AiElement[]): string {
  const lines: string[] = []

  if (project?.base_url) {
    lines.push(`Project base URL: ${project.base_url}`)
  }
  if (project?.name) {
    lines.push(`Project name: ${project.name}`)
  }
  if (project?.description) {
    lines.push(`Project description: ${project.description}`)
  }

  if (pages.length > 0) {
    lines.push('Known pages:')
    for (const page of pages.slice(0, 20)) {
      lines.push(`- ${page.name}${page.description ? `: ${page.description}` : ''}`)
    }
  }

  if (elements.length > 0) {
    lines.push('Known elements: prefer these exact selectors when intent matches.')
    for (const element of elements.slice(0, 60)) {
      const pagePrefix = element.page_name ? `[${element.page_name}] ` : ''
      const desc = element.description ? ` (${element.description})` : ''
      const alternates = getElementSelectorCandidates(element).filter((selector) => selector !== normalizeSelector(element.locator_value))
      const altText = alternates.length > 0 ? ` | AltSelectors: ${alternates.slice(0, 3).join(', ')}` : ''
      lines.push(`- ${pagePrefix}${element.name}${desc} => ${element.locator_value}${altText}`)
    }
  }

  return lines.join('\n')
}

function getStepSelectorCandidates(step: any): string[] {
  const candidates: string[] = []
  const locatorChain = step?.locator_chain

  for (const raw of [step?.target, step?.selector]) {
    const normalized = normalizeSelector(raw)
    if (normalized) candidates.push(normalized)
  }

  if (locatorChain && typeof locatorChain === 'object') {
    for (const raw of [
      locatorChain.primary,
      locatorChain.fallback_1,
      locatorChain.fallback_2,
      locatorChain.fallback_3
    ]) {
      const normalized = normalizeSelector(raw)
      if (normalized) candidates.push(normalized)
    }
  }

  return Array.from(new Set(candidates))
}

export async function loadAiContext(projectId: number | null, moduleId: number | null): Promise<AiContextBundle> {
  let project: AiProject | null = null
  let pages: AiPage[] = []
  let knownElements: AiElement[] = []

  if (projectId) {
    try {
      const projectRes = await api.get(`/projects/${projectId}`)
      project = projectRes.data
    } catch {
      project = null
    }
  }

  if (moduleId) {
    try {
      const pagesRes = await api.get(`/pages/?module_id=${moduleId}`)
      pages = pagesRes.data || []
    } catch {
      pages = []
    }
  }

  if (pages.length > 0) {
    const elementResponses = await Promise.all(
      pages.map((page) =>
        api.get(`/elements/?page_id=${page.id}`).then((res) => ({ page, elements: res.data || [] })).catch(() => ({ page, elements: [] }))
      )
    )

    knownElements = elementResponses.flatMap(({ page, elements }) =>
      elements.map((element: AiElement) => ({
        ...element,
        page_name: page.name
      }))
    )
  }

  return {
    project,
    pages,
    knownElements,
    businessRules: buildBusinessRules(project, pages, knownElements)
  }
}

export async function loadLiveAiRuntimeContext(): Promise<LiveAiRuntimeContext> {
  try {
    const res = await api.get('/recording/context')
    const data = res.data || {}
    const url = data.url ? String(data.url) : null
    const title = data.title ? String(data.title) : null
    const domSnapshot = data.dom_snapshot ? String(data.dom_snapshot) : ''
    const source = data.source ? String(data.source) : 'recording_browser'
    const available = Boolean(data.available && domSnapshot)
    const hintLines: string[] = []

    if (title) {
      hintLines.push(`Active AUT page title: ${title}`)
    }
    if (url) {
      hintLines.push(`Active AUT page URL: ${url}`)
    }
    if (source) {
      hintLines.push(`Context source: ${source}`)
    }

    return {
      available,
      source,
      url,
      title,
      domSnapshot,
      contextHint: hintLines.join('\n')
    }
  } catch {
    return {
      available: false,
      source: 'recording_browser',
      url: null,
      title: null,
      domSnapshot: '',
      contextHint: ''
    }
  }
}

export function bindGeneratedStepsToKnownElements<T extends Record<string, any>>(
  steps: T[],
  elements: AiElement[]
): { steps: T[]; boundCount: number; unboundInteractiveCount: number } {
  let boundCount = 0
  let unboundInteractiveCount = 0
  const interactiveActions = new Set(['click', 'fill', 'select', 'hover', 'press', 'wait_for_selector', 'assert_text', 'assert_visible'])

  const boundSteps = steps.map((step) => {
    const scoredMatches = elements
      .map((element) => ({
        element,
        score: scoreElementMatch(step, element)
      }))
      .sort((a, b) => b.score - a.score)
    const match = scoredMatches[0]?.score >= 70 ? scoredMatches[0].element : null

    if (!match) {
      if (interactiveActions.has(String(step.action || ''))) {
        unboundInteractiveCount += 1
      }
      return step
    }

    boundCount += 1
    return {
      ...step,
      page_id: match.page_id,
      element_id: match.id,
      target: match.locator_value,
      selector: match.locator_value,
      locator_chain: step.locator_chain && step.locator_chain.primary ? step.locator_chain : {
        primary: match.locator_value
      }
    }
  })

  return {
    steps: boundSteps,
    boundCount,
    unboundInteractiveCount
  }
}
