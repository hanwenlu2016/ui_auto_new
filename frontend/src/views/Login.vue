<template>
  <div class="login-container">
    <n-card class="login-card">
      <div class="login-header animate-fade-in">
        <h2>UI 自动化测试平台</h2>
        <p>请登录以继续</p>
      </div>
      <n-form
        ref="formRef"
        :model="formValue"
        :rules="rules"
        size="large"
        class="animate-slide-up"
      >
        <n-form-item path="email" label="邮箱">
          <n-input v-model:value="formValue.email" placeholder="admin@example.com" />
        </n-form-item>
        <n-form-item path="password" label="密码">
          <n-input
            v-model:value="formValue.password"
            type="password"
            show-password-on="click"
            placeholder="admin"
            @keydown.enter.prevent="handleLogin"
          />
        </n-form-item>
        <n-form-item>
          <n-button
            type="primary"
            block
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </n-button>
        </n-form-item>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessage, type FormInst, NCard, NForm, NFormItem, NInput, NButton } from 'naive-ui'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'

const formRef = ref<FormInst | null>(null)
const message = useMessage()
const userStore = useUserStore()
const router = useRouter()
const loading = ref(false)

const formValue = ref({
  email: 'admin@example.com',
  password: 'admin'
})

const rules = {
  email: {
    required: true,
    message: '请输入邮箱',
    trigger: 'blur'
  },
  password: {
    required: true,
    message: '请输入密码',
    trigger: 'blur'
  }
}

const handleLogin = async () => {
  formRef.value?.validate(async (errors) => {
    if (!errors) {
      loading.value = true
      try {
        await userStore.login(formValue.value)
        message.success('Login successful')
        router.push('/')
      } catch (error: any) {
        message.error(error.response?.data?.detail || 'Login failed')
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  /* GPU acceleration */
  transform: translateZ(0);
  will-change: transform;
}

.login-container::before {
  content: '';
  position: absolute;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
  background-size: 50px 50px;
  animation: moveBackground 20s linear infinite;
  /* GPU acceleration */
  transform: translateZ(0);
  will-change: transform;
}

/* Floating particles effect */
.login-container::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  background-image: 
    radial-gradient(circle, rgba(255,255,255,0.3) 2px, transparent 2px),
    radial-gradient(circle, rgba(255,255,255,0.2) 1px, transparent 1px);
  background-size: 200px 200px, 100px 100px;
  background-position: 0 0, 50px 50px;
  animation: floatParticles 30s ease-in-out infinite;
  opacity: 0.5;
}

@keyframes moveBackground {
  0% {
    transform: translate(0, 0) translateZ(0);
  }
  100% {
    transform: translate(50px, 50px) translateZ(0);
  }
}

@keyframes floatParticles {
  0%, 100% {
    transform: translateY(0) translateZ(0);
  }
  50% {
    transform: translateY(-20px) translateZ(0);
  }
}

.login-card {
  width: 420px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-radius: 24px;
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  position: relative;
  z-index: 1;
  padding: 20px;
  /* GPU acceleration */
  transform: translateZ(0);
  will-change: transform, box-shadow;
  /* Entrance animation */
  animation: cardEntrance 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes cardEntrance {
  0% {
    opacity: 0;
    transform: translateY(30px) scale(0.95) translateZ(0);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1) translateZ(0);
  }
}

.login-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #667eea, #764ba2, #667eea);
  background-size: 200% 100%;
  border-radius: 24px 24px 0 0;
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0%, 100% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.animate-fade-in {
  animation: fadeIn 0.8s ease-out 0.2s both;
}

@keyframes fadeIn {
  0% {
    opacity: 0;
    transform: translateY(-10px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-slide-up {
  animation: slideUp 0.8s ease-out 0.4s both;
}

@keyframes slideUp {
  0% {
    opacity: 0;
    transform: translateY(20px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header h2 {
  font-size: 28px;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 8px 0;
  /* Text shimmer effect */
  background-size: 200% auto;
  animation: textShimmer 3s ease-in-out infinite;
}

@keyframes textShimmer {
  0%, 100% {
    background-position: 0% center;
  }
  50% {
    background-position: 100% center;
  }
}

.login-header p {
  color: #666;
  font-size: 14px;
  margin: 0;
}

:deep(.n-form-item) {
  margin-bottom: 20px;
  /* Staggered animation for form items */
  animation: slideInLeft 0.6s ease-out both;
}

:deep(.n-form-item:nth-child(1)) {
  animation-delay: 0.5s;
}

:deep(.n-form-item:nth-child(2)) {
  animation-delay: 0.6s;
}

:deep(.n-form-item:nth-child(3)) {
  animation-delay: 0.7s;
}

@keyframes slideInLeft {
  0% {
    opacity: 0;
    transform: translateX(-20px);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
  }
}

:deep(.n-input) {
  border-radius: 12px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  /* GPU acceleration */
  transform: translateZ(0);
  will-change: box-shadow, transform;
}

:deep(.n-input:hover) {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
  transform: translateY(-1px) translateZ(0);
}

:deep(.n-input:focus-within) {
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.3);
  transform: translateY(-2px) translateZ(0);
}

:deep(.n-button) {
  border-radius: 12px;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-size: 200% auto;
  border: none;
  position: relative;
  overflow: hidden;
  /* GPU acceleration */
  transform: translateZ(0);
  will-change: transform, box-shadow, background-position;
}

:deep(.n-button::before) {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

:deep(.n-button:hover) {
  transform: translateY(-3px) translateZ(0);
  box-shadow: 0 12px 24px rgba(102, 126, 234, 0.4);
  background-position: right center;
}

:deep(.n-button:hover::before) {
  width: 300px;
  height: 300px;
}

:deep(.n-button:active) {
  transform: translateY(-1px) translateZ(0);
  transition: transform 0.1s;
}

/* Loading state animation */
:deep(.n-button.n-button--loading) {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

/* Smooth transitions for all interactive elements */
* {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Optimize rendering */
:deep(.n-input__input-el),
:deep(.n-button__content) {
  transform: translateZ(0);
}
</style>
