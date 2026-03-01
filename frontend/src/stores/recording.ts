import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useRecordingStore = defineStore('recording', () => {
    const pendingSteps = ref<any[]>([])

    const setPendingSteps = (steps: any[]) => {
        pendingSteps.value = steps
    }

    const clearPendingSteps = () => {
        pendingSteps.value = []
    }

    return {
        pendingSteps,
        setPendingSteps,
        clearPendingSteps
    }
})
