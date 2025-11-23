<template>
  <div class="projects-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-text">
        <h1>项目管理</h1>
        <p>管理您的自动化测试项目</p>
      </div>
      <n-button type="primary" @click="showCreateModal = true">
        <template #icon>
          <span style="font-size: 18px;">➕</span>
        </template>
        创建项目
      </n-button>
    </div>

    <!-- Projects Grid -->
    <div class="projects-grid">
      <n-card 
        v-for="project in projects" 
        :key="project.id"
        class="project-card"
        hoverable
      >
        <div class="project-card-header">
          <div class="project-icon">📁</div>
          <h3>{{ project.name }}</h3>
        </div>
        <p class="project-description">{{ project.description || '暂无描述' }}</p>
        <div class="project-meta">
          <span class="meta-item">
            <span class="meta-icon">📅</span>
            {{ new Date(project.created_at).toLocaleDateString() }}
          </span>
        </div>
        <div class="project-actions">
          <n-button size="small" type="primary" secondary @click="handleEdit(project)">
            编辑
          </n-button>
          <n-button size="small" type="error" secondary @click="handleDelete(project)">
            删除
          </n-button>
        </div>
      </n-card>

      <!-- Empty State -->
      <n-card v-if="!loading && projects.length === 0" class="empty-state">
        <n-empty description="还没有项目，创建一个开始吧！" />
      </n-card>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <n-spin size="large" />
    </div>

    <!-- Create/Edit Modal -->
    <n-modal v-model:show="showCreateModal" :mask-closable="false">
      <n-card
        style="width: 600px"
        :title="editingId ? '✏️ 编辑项目' : '➕ 创建项目'"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        class="modal-card"
      >
        <n-form
          ref="formRef"
          :model="formValue"
          :rules="rules"
          label-placement="top"
        >
          <n-form-item label="📝 项目名称" path="name">
            <n-input 
              v-model:value="formValue.name" 
              placeholder="请输入项目名称" 
              size="large"
            />
          </n-form-item>
          <n-form-item label="🌐 基础URL" path="base_url">
            <n-input 
              v-model:value="formValue.base_url" 
              placeholder="请输入网站基础URL (例如: https://example.com)" 
              size="large"
            />
          </n-form-item>
          <n-form-item label="📄 项目描述" path="description">
            <n-input
              v-model:value="formValue.description"
              type="textarea"
              placeholder="请输入项目描述（可选）"
              :autosize="{ minRows: 3, maxRows: 6 }"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <n-space justify="end">
            <n-button @click="handleCloseModal" size="large">取消</n-button>
            <n-button type="primary" @click="handleCreate" size="large">
              {{ editingId ? '更新' : '创建' }}
            </n-button>
          </n-space>
        </template>
      </n-card>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NSpace, useMessage, type FormInst, NCard, NModal, NForm, NFormItem, NInput, NSpin, NEmpty } from 'naive-ui'
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
          message.success('项目更新成功')
        } else {
          await api.post('/projects/', formValue.value)
          message.success('项目创建成功')
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
    message.success('项目删除成功')
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
.projects-container {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 16px 24px;
  border-radius: 4px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
}

.header-text h1 {
  font-size: 20px;
  font-weight: 500;
  color: #1f2225;
  margin: 0 0 4px 0;
}

.header-text p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.project-card {
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.project-card:hover {
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.16), 0 3px 6px 0 rgba(0, 0, 0, 0.12), 0 5px 12px 4px rgba(0, 0, 0, 0.09);
  transform: translateY(-2px);
}

.project-card :deep(.n-card__content) {
  padding: 20px;
}

.project-card-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.project-icon {
  font-size: 24px;
  margin-right: 12px;
  color: #2d8cf0;
  background: #e6f7ff;
  width: 40px;
  height: 40px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.project-card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #17233d;
}

.project-description {
  color: #808695;
  font-size: 14px;
  line-height: 1.5;
  margin: 0 0 16px 0;
  height: 42px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.project-meta {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #c5c8ce;
  margin-bottom: 16px;
  padding-top: 12px;
  border-top: 1px solid #e8eaec;
}

.meta-icon {
  margin-right: 4px;
}

.project-actions {
  display: flex;
  gap: 8px;
}

.project-actions :deep(.n-button) {
  flex: 1;
}

/* Empty State */
.empty-state {
  grid-column: 1 / -1;
  border-radius: 4px;
  border: 1px dashed #dcdee2;
  background: white;
}

.empty-state :deep(.n-card__content) {
  padding: 40px;
}

/* Loading */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

/* Modal */
.modal-card {
  border-radius: 4px;
}

.modal-card :deep(.n-card-header) {
  padding: 16px 24px;
  border-bottom: 1px solid #e8eaec;
  font-size: 16px;
  font-weight: 500;
}

/* Responsive */
@media (max-width: 768px) {
  .projects-grid {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
}
</style>
