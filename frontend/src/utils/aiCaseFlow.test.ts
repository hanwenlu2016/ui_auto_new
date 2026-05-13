import assert from 'node:assert/strict'
import test from 'node:test'
import {
  ensureAICaseModule,
  generateCaseName,
  normalizeGeneratedSteps,
} from './aiCaseFlow.ts'
import type { CreateModulePayload, GeneratedStep, ModuleSummary } from './aiCaseFlow.ts'

test('normalizeGeneratedSteps converts goto target into value and infers descriptions', () => {
  const input: GeneratedStep[] = [
    { action: '打开', target: 'https://example.com' },
    { action: '等待', value: '2s' },
    { action: '点击', target: '#submit' },
  ]

  const steps = normalizeGeneratedSteps(input)

  assert.equal(steps[0].action, 'goto')
  assert.equal(steps[0].target, '')
  assert.equal(steps[0].value, 'https://example.com')
  assert.equal(steps[0].description, '访问页面 https://example.com')

  assert.equal(steps[1].action, 'wait')
  assert.equal(steps[1].wait_ms, 2000)
  assert.equal(steps[1].value, '2000')
  assert.equal(steps[1].description, '等待 2s')

  assert.equal(steps[2].action, 'click')
  assert.equal(steps[2].description, '点击 #submit')
})

test('ensureAICaseModule reuses existing default AI module', async () => {
  const calls: string[] = []
  const moduleId = await ensureAICaseModule({
    projectId: 9,
    fetchModules: async (projectId: number): Promise<ModuleSummary[]> => {
      calls.push(`get:${projectId}`)
      return [
        { id: 1, name: '登录模块', project_id: projectId },
        { id: 2, name: 'AI 生成用例', project_id: projectId },
      ]
    },
    createModule: async (_payload: CreateModulePayload): Promise<ModuleSummary> => {
      throw new Error('should not create module when default exists')
    },
  })

  assert.equal(moduleId, 2)
  assert.deepEqual(calls, ['get:9'])
})

test('ensureAICaseModule creates default AI module when missing', async () => {
  const calls: string[] = []
  const moduleId = await ensureAICaseModule({
    projectId: 7,
    fetchModules: async (projectId: number): Promise<ModuleSummary[]> => {
      calls.push(`get:${projectId}`)
      return [{ id: 4, name: '订单模块', project_id: projectId }]
    },
    createModule: async (payload: CreateModulePayload): Promise<ModuleSummary> => {
      calls.push(`post:${payload.project_id}:${payload.name}`)
      return { id: 12, name: payload.name, project_id: payload.project_id }
    },
  })

  assert.equal(moduleId, 12)
  assert.deepEqual(calls, ['get:7', 'post:7:AI 生成用例'])
})

test('generateCaseName prefers prompt summary and first action', () => {
  const steps: GeneratedStep[] = [
    { action: 'goto', description: '访问页面 https://www.baidu.com' },
    { action: 'fill', description: '输入 Vue3 教程 到搜索框' },
  ]

  const name = generateCaseName({
    prompt: '打开百度搜索 Vue3 教程 并点击第一条结果',
    steps,
  })

  assert.equal(name, '打开百度搜索 Vue3 教程 并点击第一条结果')
})
