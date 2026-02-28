<template>
  <div class="page-container animate-fade-up">
    <!-- Page Header -->
    <div class="page-header">
      <div>
        <h1>项目管理</h1>
        <p>管理您的自动化测试项目集合</p>
      </div>
      <n-button type="primary" @click="showCreateModal = true">
        <template #icon>
          <span style="font-size: 16px;">➕</span>
        </template>
        创建项目
      </n-button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <n-spin size="large" />
    </div>

    <!-- Empty State -->
    <div v-else-if="projects.length === 0" class="empty-wrap animate-fade-up">
      <div style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;">🗂</div>
      <div style="font-size: 16px; color: var(--color-text-2); font-weight: 500; margin-bottom: 8px;">暂无项目</div>
      <div style="font-size: 13px; color: var(--color-text-3); margin-bottom: 24px;">创建一个新项目开始自动化测试之旅吧！</div>
      <n-button type="primary" @click="showCreateModal = true">立即创建</n-button>
    </div>

    <!-- Projects Grid -->
    <div v-else class="projects-grid">
      <div 
        v-for="(project, i) in projects" 
        :key="project.id"
        class="project-card card-hoverable animate-fade-up"
        :style="{ animationDelay: `${i * 0.05}s` }"
      >
        <div class="project-card-header">
          <div class="project-icon">📁</div>
          <h3 class="project-title">{{ project.name }}</h3>
        </div>
        
        <p class="project-description">{{ project.description || '暂无描述' }}</p>
        
        <div class="project-url">
          <span class="url-icon">🔗</span>
          <a :href="project.base_url" target="_blank" class="url-text">{{ project.base_url || '未设置基础URL' }}</a>
        </div>
        
        <div class="project-footer">
          <div class="project-meta">
            <span class="meta-icon">📅</span>
            {{ new Date(project.created_at).toLocaleDateString() }}
          </div>
          <div class="project-actions">
            <n-button size="small" tertiary type="primary" @click.stop="handleEdit(project)">编辑</n-button>
            <n-button size="small" tertiary type="error" @click.stop="handleDelete(project)">删除</n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal" :mask-closable="false">
      <n-card
        style="width: 500px; max-width: 90vw"
        :title="editingId ? '✏️ 编辑项目' : '➕ 创建项目'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <n-form
          ref="formRef"
          :model="formValue"
          :rules="rules"
          label-placement="top"
          size="medium"
        >
          <n-form-item label="项目名称" path="name">
            <n-input v-model:value="formValue.name" placeholder="输入项目名称" />
          </n-form-item>
          <n-form-item label="基础 URL" path="base_url">
            <n-input v-model:value="formValue.base_url" placeholder="https://..." />
          </n-form-item>
          <n-form-item label="项目描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="添加描述信息（可选）"
              :autosize="{ minRows: 3, maxRows: 5 }"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <div style="display: flex; justify-content: flex-end; gap: 12px;">
            <n-button @click="handleCloseModal">取消</n-button>
            <n-button type="primary" @click="handleCreate">
              {{ editingId ? '保存更改' : '确认创建' }}
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

const formValue = ref({
  name: '',
  description: '',
  base_url: ''
})

const rules = {
  name: {
    required: true,
    message: '请输入项目名称',
    trigger: 'blur'
  }
}

const fetchProjects = async () => {
  loading.value = true
  try {
    const response = await api.get('/projects/')
    projects.value = response.data
  } catch (error) {
    message.error('获取项目列表失败')
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
          message.success('项目已更新')
        } else {
          await api.post('/projects/', formValue.value)
          message.success('新项目已创建')
        }
        handleCloseModal()
        fetchProjects()
      } catch (error) {
        message.error(editingId.value ? '更新项目失败' : '创建项目失败')
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
    message.success('项目已删除')
    fetchProjects()
  } catch (error) {
    message.error('删除项目失败')
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.project-card {
  background: var(--color-card);
  border-radius: 16px;
  border: 1px solid var(--color-divider);
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.project-card-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.project-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  margin-right: 14px;
  flex-shrink: 0;
}

.project-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-1);
}

.project-description {
  color: var(--color-text-2);
  font-size: 13px;
  line-height: 1.6;
  margin: 0 0 16px 0;
  height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.project-url {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--color-bg);
  padding: 8px 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 12px;
}

.url-icon {
  font-size: 14px;
  color: var(--color-text-3);
}

.url-text {
  color: var(--color-text-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid var(--color-divider);
}

.project-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-3);
  font-weight: 500;
}

.project-actions {
  display: flex;
  gap: 8px;
  opacity: 0;
  transform: translateX(4px);
  transition: all 0.2s ease;
}

.project-card:hover .project-actions {
  opacity: 1;
  transform: translateX(0);
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}
</style>
