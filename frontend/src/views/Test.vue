<template>
  <div style="padding: 20px;">
    <h1>Naive UI Component Test</h1>
    <n-space vertical>
      <n-input placeholder="Test Input" />
      <n-button>Test Button</n-button>
      <n-card title="Test Card">
        <n-form>
          <n-form-item label="Email">
            <n-input placeholder="Email" />
          </n-form-item>
          <n-form-item label="Password">
            <n-input type="password" placeholder="Password" />
          </n-form-item>
        </n-form>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { NSpace, NInput, NButton, NCard, NForm, NFormItem } from 'naive-ui'
</script>
