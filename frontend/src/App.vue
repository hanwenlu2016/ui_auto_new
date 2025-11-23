<template>
  <n-config-provider :theme-overrides="adminTheme">
    <n-global-style />
    <n-message-provider>
      <n-dialog-provider>
        <router-view />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { NConfigProvider, NMessageProvider, NDialogProvider, NGlobalStyle } from 'naive-ui'
import { adminTheme } from '@/theme'
</script>

<style>
body {
  margin: 0;
  font-family: v-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
}
</style>
