<template>
  <div class="login-container">
    <!-- Subtle Background Shapes -->
    <div class="shape shape-1"></div>
    <div class="shape shape-2"></div>
    
    <div class="login-box animate-scale-up">
      <!-- Left Side: Illustration -->
      <div class="login-left">
        <div class="illustration-wrap">
          <img src="@/assets/login_illustration.png" alt="Automation Illustration" class="floating-img" />
        </div>
        <div class="tech-stack-info">
          <span>Vue 3</span>
          <span class="dot"></span>
          <span>FastAPI</span>
          <span class="dot"></span>
          <span>Playwright</span>
        </div>
      </div>

      <!-- Right Side: Form -->
      <div class="login-right">
        <div class="form-container">
          <div class="brand-header">
            <div class="logo-box">
              <span class="logo-icon">🤖</span>
            </div>
            <div class="brand-names">
              <h2>UI-Ai-Uutomation</h2>
              <p>智能 UI 自动化测试平台</p>
            </div>
          </div>

          <n-form
            ref="formRef"
            :model="formValue"
            :rules="rules"
            size="large"
            label-placement="top"
            class="login-form"
          >
            <n-form-item path="email" label="账号">
              <n-input 
                v-model:value="formValue.email" 
                placeholder="admin@example.com" 
                class="custom-input"
              >
                <template #prefix>
                  <span class="input-icon">👤</span>
                </template>
              </n-input>
            </n-form-item>
            
            <n-form-item path="password" label="密码">
              <n-input
                v-model:value="formValue.password"
                type="password"
                show-password-on="click"
                placeholder="admin"
                class="custom-input"
                @keydown.enter.prevent="handleLogin"
              >
                <template #prefix>
                  <span class="input-icon">🔑</span>
                </template>
              </n-input>
            </n-form-item>

            <div class="form-options">
              <n-checkbox v-model:checked="rememberMe">记住我</n-checkbox>
              <n-button text type="primary" size="tiny">忘记密码？</n-button>
            </div>

            <div class="action-area">
              <n-button
                type="primary"
                block
                :loading="loading"
                @click="handleLogin"
                class="login-btn"
              >
                登 录
              </n-button>
            </div>
          </n-form>
        </div>
        
        <div class="login-footer">
          <p>© 2026 HanWenLu. All rights reserved.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessage, type FormInst, NForm, NFormItem, NInput, NButton, NCheckbox } from 'naive-ui'
import { useUserStore } from '@/stores/user'

const formRef = ref<FormInst | null>(null)
const message = useMessage()
const userStore = useUserStore()
const loading = ref(false)
const rememberMe = ref(true)

const formValue = ref({
  email: 'admin@example.com',
  password: 'admin'
})

const rules = {
  email: { required: true, message: '请输入账号', trigger: 'blur' },
  password: { required: true, message: '请输入密码', trigger: 'blur' }
}

const handleLogin = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors) {
      loading.value = true
      try {
        await userStore.login(formValue.value)
        message.success('登录成功，欢迎回来')
        setTimeout(() => { window.location.href = "/"; }, 500);
      } catch (error: any) {
        message.error(error.response?.data?.detail || '认证失败，请检查账号密码')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #f0f2f5;
  background-image: radial-gradient(#d1d5db 0.5px, transparent 0.5px);
  background-size: 20px 20px;
  position: relative;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

/* Background Shapes */
.shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  z-index: 1;
  opacity: 0.4;
}

.shape-1 {
  width: 400px;
  height: 400px;
  background: #e0e7ff;
  top: -100px;
  left: -100px;
}

.shape-2 {
  width: 300px;
  height: 300px;
  background: #fdf2f8;
  bottom: -50px;
  right: -50px;
}

/* Main Box */
.login-box {
  display: flex;
  width: 900px;
  height: 560px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  position: relative;
  z-index: 10;
}

/* Left Side */
.login-left {
  flex: 1.1;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  border-right: 1px solid #f1f5f9;
}

.illustration-wrap {
  width: 100%;
  max-width: 400px;
}

.floating-img {
  width: 100%;
  height: auto;
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-15px); }
}

.tech-stack-info {
  margin-top: 40px;
  color: #94a3b8;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.tech-stack-info .dot {
  width: 4px;
  height: 4px;
  background: #cbd5e1;
  border-radius: 50%;
}

/* Right Side */
.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 60px 50px;
}

.form-container {
  flex: 1;
}

.brand-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 40px;
}

.logo-box {
  width: 48px;
  height: 48px;
  background: #fff;
  border: 1px solid #fee2e2;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  box-shadow: 0 4px 10px rgba(239, 68, 68, 0.1);
}

.brand-names h2 {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
  margin: 0;
}

.brand-names p {
  font-size: 12px;
  color: #64748b;
  margin: 2px 0 0 0;
}

.login-form {
  width: 100%;
}

:deep(.n-form-item-label) {
  font-weight: 600;
  color: #475569;
  font-size: 13px;
  margin-bottom: 4px;
}

/* Custom Input */
:deep(.custom-input .n-input-wrapper) {
  background-color: #fff !important;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.2s;
  padding: 4px 8px;
}

:deep(.custom-input:hover .n-input-wrapper) {
  border-color: #cbd5e1;
}

:deep(.custom-input:focus-within .n-input-wrapper) {
  border-color: #f97316; /* 橙色对标参考 UI */
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.1);
}

.input-icon {
  font-size: 16px;
  margin-right: 8px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: -10px 0 24px 0;
}

:deep(.n-checkbox-label) {
  font-size: 12px;
  color: #64748b;
}

/* Login Button */
.action-area {
  margin-top: 32px;
}

.login-btn {
  height: 48px;
  background-color: #f97316; /* 橙色对标参考 UI */
  border-radius: 8px;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: 2px;
  border: none;
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.2);
  transition: all 0.3s;
}

.login-btn:hover {
  background-color: #ea580c;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(249, 115, 22, 0.3);
}

/* Footer */
.login-footer {
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}

/* Animations */
.animate-scale-up {
  animation: scaleUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes scaleUp {
  from { opacity: 0; transform: scale(0.95) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* Responsive */
@media (max-width: 992px) {
  .login-box {
    width: 90%;
    max-width: 500px;
    height: auto;
    flex-direction: column;
  }
  .login-left {
    display: none;
  }
}
</style>
