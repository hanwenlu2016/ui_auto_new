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

function normalizeSelector(selector: string | null | undefined): string {
  return String(selector || '')
    .trim()
    .replace(/:visible\b/gi, '')
    .replace(/\s+/g, ' ')
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
      lines.push(`- ${pagePrefix}${element.name}${desc} => ${element.locator_value}`)
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

export function bindGeneratedStepsToKnownElements<T extends Record<string, any>>(
  steps: T[],
  elements: AiElement[]
): { steps: T[]; boundCount: number; unboundInteractiveCount: number } {
  let boundCount = 0
  let unboundInteractiveCount = 0
  const interactiveActions = new Set(['click', 'fill', 'select', 'hover', 'press', 'wait_for_selector', 'assert_text', 'assert_visible'])

  const boundSteps = steps.map((step) => {
    const selectorCandidates = getStepSelectorCandidates(step)
    const match = elements.find((element) =>
      selectorCandidates.some((candidate) => normalizeSelector(element.locator_value) === candidate)
    )

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
      locator_chain: step.locator_chain || {
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
