<template>
  <div class="ai-models-container">
    <div class="page-header">
      <div class="header-left">
        <n-gradient-text type="primary" :size="28" weight="800">AI 引擎配置</n-gradient-text>
        <p class="header-desc">统一管理自动化测试所需的 AI 模型，支持多厂商接入与默认引擎切换。</p>
      </div>
      <n-button type="primary" @click="showModal = true">
        <template #icon><n-icon><add-icon /></n-icon></template>
        添加新模型
      </n-button>
    </div>

    <n-grid :cols="24" :x-gap="20" :y-gap="20">
      <n-gi :span="24" v-if="loading">
        <div class="loading-state">
          <n-spin size="large" />
          <p>正在加载 AI 配置...</p>
        </div>
      </n-gi>

      <n-gi :span="24" v-else-if="models.length === 0">
        <div class="empty-state">
          <div class="empty-icon">🤖</div>
          <h3>尚未配置 AI 引擎</h3>
          <p>添加一个 OpenAI 兼容的模型（如 DeepSeek, MiniMax, GLM）来开启 AI 自动化之旅。</p>
          <n-button type="primary" secondary @click="showModal = true">立即添加</n-button>
        </div>
      </n-gi>

      <n-gi :span="8" v-for="model in models" :key="model.id" v-else>
        <n-card class="model-card" :class="{ 'is-default': model.is_default }">
          <template #header>
            <div class="card-header">
              <span class="model-name">{{ model.name }}</span>
              <n-tag v-if="model.is_default" type="primary" size="small" round primary>默认</n-tag>
            </div>
          </template>

          <div class="card-content">
            <div class="info-item">
              <span class="label">型号:</span>
              <span class="value">{{ model.model_identifier }}</span>
            </div>
            <div class="info-item">
              <span class="label">地址:</span>
              <n-ellipsis style="max-width: 180px" :content="model.base_url" />
            </div>
            <div class="info-item">
              <span class="label">状态:</span>
              <n-switch v-model:value="model.is_active" size="small" @update:value="handleStatusChange(model)" />
            </div>
          </div>

          <template #footer>
            <div class="card-footer">
              <div class="footer-left">
                <n-button quaternary size="small" type="primary" @click="setAsDefault(model)" :disabled="model.is_default">设为默认</n-button>
                <n-button
                  quaternary
                  size="small"
                  @click="testModelConnection(model)"
                  :loading="testingModelId === model.id"
                >
                  测试连接
                </n-button>
              </div>
              <div class="footer-right">
                <n-button quaternary circle size="small" @click="editModel(model)">
                  <template #icon><n-icon><edit-icon /></n-icon></template>
                </n-button>
                <n-popconfirm @positive-click="deleteModel(model.id)" title="确定删除此配置吗？">
                  <template #trigger>
                    <n-button quaternary circle size="small" type="error">
                      <template #icon><n-icon><trash-icon /></n-icon></template>
                    </n-button>
                  </template>
                </n-popconfirm>
              </div>
            </div>
          </template>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Modal for Create/Edit -->
    <n-modal v-model:show="showModal" preset="card" :title="form.id ? '编辑 AI 模型' : '添加 AI 模型'" style="width: 550px">
      <n-form :model="form" label-placement="left" label-width="100" require-mark-placement="right-hanging">
        <n-form-item label="显示名称" path="name">
          <n-input v-model:value="form.name" placeholder="例如: DeepSeek-V3 官方" />
        </n-form-item>
        <n-form-item label="API 地址" path="base_url">
          <n-input v-model:value="form.base_url" placeholder="https://api.deepseek.com" />
        </n-form-item>
        <n-form-item label="模型标识" path="model_identifier">
          <n-input v-model:value="form.model_identifier" placeholder="deepseek-chat" />
        </n-form-item>
        <n-form-item label="API Key" path="api_key">
          <n-input v-model:value="form.api_key" type="password" show-password-on="mousedown" placeholder="sk-..." />
        </n-form-item>
        <n-form-item label="设为默认" path="is_default">
          <n-checkbox v-model:checked="form.is_default">设为系统默认引擎</n-checkbox>
        </n-form-item>
      </n-form>
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 12px">
          <n-button @click="showModal = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存配置</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  NGradientText, NButton, NIcon, NGrid, NGi, NCard, NTag, NSwitch, 
  NEllipsis, NModal, NForm, NFormItem, NInput, NCheckbox, NPopconfirm, NSpin, useMessage 
} from 'naive-ui'
import { 
  AddOutline as AddIcon, 
  CreateOutline as EditIcon, 
  TrashOutline as TrashIcon 
} from '@vicons/ionicons5'
import api from '@/api'

const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const showModal = ref(false)
const models = ref<any[]>([])
const testingModelId = ref<number | null>(null)

const initialForm = {
  id: null,
  name: '',
  base_url: '',
  model_identifier: '',
  api_key: '',
  is_default: false,
  is_active: true
}
const form = ref({...initialForm})

const fetchModels = async () => {
  loading.value = true
  try {
    const res = await api.get('/ai-models/')
    models.value = res.data
  } catch (err) {
    message.error('加载模型列表失败')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    if (form.value.id) {
      await api.put(`/ai-models/${form.value.id}`, form.value)
      message.success('更新成功')
    } else {
      await api.post('/ai-models/', form.value)
      message.success('添加成功')
    }
    showModal.value = false
    form.value = {...initialForm}
    fetchModels()
  } catch (err) {
    message.error('保存失败，请检查配置')
  } finally {
    saving.value = false
  }
}

const editModel = (model: any) => {
  form.value = { ...model }
  showModal.value = true
}

const deleteModel = async (id: number) => {
  try {
    await api.delete(`/ai-models/${id}`)
    message.success('删除成功')
    fetchModels()
  } catch (err) {
    message.error('删除失败')
  }
}

const setAsDefault = async (model: any) => {
  try {
    await api.put(`/ai-models/${model.id}`, { ...model, is_default: true })
    message.success(`${model.name} 已设为默认引擎`)
    fetchModels()
  } catch (err) {
    message.error('设置默认引擎失败')
  }
}

const handleStatusChange = async (model: any) => {
  try {
    await api.put(`/ai-models/${model.id}`, { is_active: model.is_active })
  } catch (err) {
    message.error('更新状态失败')
    fetchModels()
  }
}

const testModelConnection = async (model: any) => {
  testingModelId.value = model.id
  try {
    const res = await api.post(`/ai-models/${model.id}/test`)
    const result = res.data
    if (result.success) {
      const latency = result.latency_ms !== null && result.latency_ms !== undefined
        ? `（${result.latency_ms}ms）`
        : ''
      const summary = result.provider_message ? ` 返回: ${result.provider_message}` : ''
      message.success(`连接成功 ${latency}${summary}`)
    } else {
      const errorType = result.error_type || 'unknown_error'
      const errorMessage = result.error_message || '未知错误'
      message.error(`连接失败 [${errorType}] ${errorMessage}`)
    }
  } catch (err: any) {
    message.error(err?.response?.data?.detail || '连接测试失败')
  } finally {
    testingModelId.value = null
  }
}

onMounted(fetchModels)
</script>

<style scoped>
.ai-models-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-desc {
  color: #666;
  margin-top: 8px;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  text-align: center;
}

.empty-icon { font-size: 64px; margin-bottom: 16px; }
.empty-state h3 { font-size: 20px; color: #333; margin-bottom: 8px; }
.empty-state p { color: #888; margin-bottom: 24px; max-width: 400px; margin-left: auto; margin-right: auto; }

.model-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid var(--color-divider);
  border-radius: 16px;
}

.model-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.06);
}

.model-card.is-default {
  border-color: var(--color-primary);
  background: linear-gradient(to bottom right, #ffffff, #f0f4ff);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-name {
  font-weight: 700;
  font-size: 17px;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin: 16px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.info-item .label { color: #888; }
.info-item .value { font-weight: 500; }

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-left {
  display: flex;
  gap: 8px;
}

.footer-right {
  display: flex;
  gap: 8px;
}
</style>
