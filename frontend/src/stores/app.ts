import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
    const selectedProjectId = ref<number | null>(null)
    const selectedModuleId = ref<number | null>(null)

    const setProjectId = (id: number | null) => {
        selectedProjectId.value = id
    }

    const setModuleId = (id: number | null) => {
        selectedModuleId.value = id
    }

    return {
        selectedProjectId,
        selectedModuleId,
        setProjectId,
        setModuleId
    }
})
