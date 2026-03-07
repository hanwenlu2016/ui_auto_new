<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header (Premium Gradient) -->
    <div class="page-header-premium">
      <div class="header-content">
        <h1 class="gradient-text">项目指挥中心</h1>
        <p>集中管理自动化测试项目，驱动业务质量演进</p>
      </div>
      <n-button type="primary" size="large" @click="showCreateModal = true" class="shadow-primary">
        <template #icon>
          <span style="font-size: 18px;">➕</span>
        </template>
        创建新项目
      </n-button>
    </div>

    <!-- Overview Stats Bar (New) -->
    <div class="stats-bar animate-fade-up" style="animation-delay: 0.1s">
      <div class="stat-item">
        <div class="stat-icon-mini" style="background: rgba(79,129,255,0.1); color: var(--color-primary);">🗂</div>
        <div class="stat-info">
          <span class="stat-label">总项目数</span>
          <span class="stat-value">{{ projects.length }}</span>
        </div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-icon-mini" style="background: rgba(52,211,153,0.1); color: #10B981;">🧪</div>
        <div class="stat-info">
          <span class="stat-label">关联模块</span>
          <span class="stat-value">--</span>
        </div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-icon-mini" style="background: rgba(251,146,60,0.1); color: #F59E0B;">🚀</div>
        <div class="stat-info">
          <span class="stat-label">近期执行</span>
          <span class="stat-value">--</span>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <n-spin size="large" />
    </div>

    <!-- Empty State (Redesigned) -->
    <div v-else-if="projects.length === 0" class="empty-wrap animate-fade-up">
      <div class="empty-icon-wrap">
        <div class="empty-bg-glow"></div>
        <div class="empty-main-icon">🗂</div>
      </div>
      <h2 style="font-size: 20px; font-weight: 700; color: var(--color-text-1); margin-bottom: 8px;">开启您的第一个项目</h2>
      <p style="font-size: 14px; color: var(--color-text-3); max-width: 320px; margin-bottom: 32px;">
        配置基础 URL 即可开始自动化测试流程。我们的 AI 将协助您快速生成执行链路。
      </p>
      <n-button type="primary" size="large" @click="showCreateModal = true" class="shadow-primary">立即创建</n-button>
    </div>

    <!-- Projects Grid (Modern Cards) -->
    <div v-else class="projects-grid">
      <div 
        v-for="(project, i) in projects" 
        :key="project.id"
        class="project-v-card animate-fade-up"
        :style="{ animationDelay: `${0.2 + i * 0.06}s` }"
      >
        <div class="card-top-accent"></div>
        <div class="card-inner">
          <div class="p-card-header">
            <div class="p-icon-box" :style="{ background: projectGradients[i % projectGradients.length] }">
              {{ project.name.charAt(0).toUpperCase() }}
            </div>
            <div class="p-title-area">
              <h3 class="p-name">{{ project.name }}</h3>
              <span class="p-badge">Stable</span>
            </div>
            <div class="p-more-actions">
              <n-button quaternary circle size="small" @click.stop="handleEdit(project)">
                <template #icon><span>✏️</span></template>
              </n-button>
            </div>
          </div>
          
          <div class="p-body">
            <p class="p-desc">{{ project.description || '为该项目添加描述，让团队更好地协作...' }}</p>
            
            <div class="p-link-container">
              <div class="p-link-label">BASE URL</div>
              <div class="p-link-val">
                <span class="p-link-icon">🔗</span>
                <a :href="project.base_url" target="_blank" class="p-link-a">{{ project.base_url || '未配置' }}</a>
              </div>
            </div>
          </div>
          
          <div class="p-footer">
            <div class="p-meta">
              <span class="p-meta-item">
                <span class="meta-dot" style="background: #10B981;"></span>
                Active
              </span>
              <span class="p-meta-sep"></span>
              <span class="p-meta-date">Created {{ new Date(project.created_at).toLocaleDateString() }}</span>
            </div>
            <n-button text type="error" size="tiny" @click.stop="handleDelete(project)" class="p-del-btn">
              删除项目
            </n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal (Aesthetic Update) -->
    <n-modal v-model:show="showCreateModal" :mask-closable="false">
      <n-card
        style="width: 520px; max-width: 90vw; border-radius: 20px;"
        :title="editingId ? '✏️ 编辑项目信息' : '➕ 创建自动化项目'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        class="glass-modal"
      >
        <n-form
          ref="formRef"
          :model="formValue"
          :rules="rules"
          label-placement="top"
          size="large"
          style="margin-top: 10px"
        >
          <n-form-item label="项目名称 (Unique)" path="name">
            <n-input v-model:value="formValue.name" placeholder="例如：电商系统、移动端H5..." />
          </n-form-item>
          <n-form-item label="测试目标 URL" path="base_url">
            <n-input v-model:value="formValue.base_url" placeholder="https://example.com" />
          </n-form-item>
          <n-form-item label="功能描述 / 环境信息" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="详细记录该项目适用的测试环境、账号前缀等信息..."
              :autosize="{ minRows: 3, maxRows: 5 }"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button ghost @click="handleCloseModal">返回</n-button>
            <n-button type="primary" class="shadow-primary" @click="handleCreate">
              {{ editingId ? '保存变更' : '立即初始化' }}
            </n-button>
          </div>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, useMessage, type FormInst, NCard, NModal, NForm, NFormItem, NInput, NSpin } from 'naive-ui'
import api from '@/api'

interface Project {
  id: number
  name: string
  description: string
  base_url: string
  created_at: string
}

const message = useMessage()
const loading = ref(false)
const projects = ref<Project[]>([])
const showCreateModal = ref(false)
const formRef = ref<FormInst | null>(null)
const editingId = ref<number | null>(null)

const projectGradients = [
  'linear-gradient(135deg, #4F81FF 0%, #3B5BFF 100%)',
  'linear-gradient(135deg, #10B981 0%, #059669 100%)',
  'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)',
  'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)',
  'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)'
]

const formValue = ref({
  name: '',
  description: '',
  base_url: ''
})

const rules = {
  name: { required: true, message: '必须提供项目名称以进行区分', trigger: 'blur' }
}

const fetchProjects = async () => {
  loading.value = true
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
  } catch (error) {
    message.error('信号同步失败：无法连接到项目数据库')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors) {
      try {
        if (editingId.value) {
          await api.put(`/projects/${editingId.value}`, formValue.value)
          message.success('数据库记录已更新')
        } else {
          await api.post('/projects/', formValue.value)
          message.success('新测试节点已就绪')
        }
        handleCloseModal()
        fetchProjects()
      } catch (error) {
        message.error('操作中断：无法写入磁盘')
      }
    }
  })
}

const handleEdit = (row: Project) => {
  editingId.value = row.id
  formValue.value = {
    name: row.name,
    description: row.description,
    base_url: row.base_url
  }
  showCreateModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  formValue.value = { name: '', description: '', base_url: '' }
  editingId.value = null
}

const handleDelete = async (row: Project) => {
  try {
    await api.delete(`/projects/${row.id}`)
    message.info('项目资源已卸载')
    fetchProjects()
  } catch (error) {
    message.error('操作失败：项目当前可能正在被锁定执行')
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.page-header-premium {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 32px;
  background: linear-gradient(to right, #ffffff, #fcfdfe);
  padding: 24px 0;
  border-bottom: 1px solid rgba(0,0,0,0.03);
}

.gradient-text {
  background: linear-gradient(135deg, var(--color-text-1) 0%, #4F81FF 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-size: 30px;
  font-weight: 800;
  margin-bottom: 8px;
}

.header-content p {
  color: var(--color-text-3);
  font-size: 15px;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  align-items: center;
  background: #ffffff;
  padding: 16px 24px;
  border-radius: 16px;
  margin-bottom: 32px;
  border: 1px solid var(--color-divider);
  box-shadow: 0 4px 12px rgba(0,0,0,0.02);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.stat-icon-mini {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 11px;
  color: var(--color-text-3);
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-1);
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: var(--color-divider);
  margin: 0 32px;
}

/* Project Grid & Cards */
.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 24px;
}

.project-v-card {
  background: #ffffff;
  border-radius: 20px;
  border: 1px solid var(--color-divider);
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.project-v-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 24px rgba(79, 129, 255, 0.1);
  border-color: rgba(79, 129, 255, 0.2);
}

.card-top-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(to right, transparent, rgba(79, 129, 255, 0.4), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.project-v-card:hover .card-top-accent {
  opacity: 1;
}

.card-inner {
  padding: 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.p-card-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.p-icon-box {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  margin-right: 16px;
  box-shadow: 0 6px 12px rgba(0,0,0,0.1);
}

.p-title-area {
  flex: 1;
}

.p-name {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-1);
  margin-bottom: 2px;
}

.p-badge {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
  font-weight: 700;
  text-transform: uppercase;
}

.p-desc {
  font-size: 13px;
  color: var(--color-text-2);
  line-height: 1.6;
  margin-bottom: 20px;
  height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.p-link-container {
  background: #f8faff;
  padding: 12px 14px;
  border-radius: 12px;
  margin-top: auto;
}

.p-link-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 4px;
  opacity: 0.8;
}

.p-link-val {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

.p-link-val a {
  font-size: 12px;
  color: var(--color-text-1);
  text-decoration: none;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.p-link-val a:hover {
  text-decoration: underline;
}

.p-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed var(--color-divider);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.p-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.p-meta-item {
  font-size: 12px;
  color: var(--color-text-2);
  display: flex;
  align-items: center;
  font-weight: 600;
}

.meta-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 6px;
}

.p-meta-date {
  font-size: 11px;
  color: var(--color-text-3);
}

.p-del-btn {
  opacity: 0.4;
  transition: opacity 0.2s;
}

.p-del-btn:hover {
  opacity: 1;
}

/* Empty State */
.empty-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 80px 0;
}

.empty-icon-wrap {
  position: relative;
  width: 120px;
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.empty-main-icon {
  font-size: 64px;
  z-index: 1;
}

.empty-bg-glow {
  position: absolute;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(79,129,255,0.15) 0%, transparent 70%);
  filter: blur(8px);
}

/* Animations & Shadows */
.shadow-primary {
  box-shadow: 0 4px 14px rgba(79, 129, 255, 0.35);
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

@media (max-width: 640px) {
  .page-header-premium {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
