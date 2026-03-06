import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface TabItem {
    label: string
    name: string
    path: string
    closable?: boolean
}

export const useTabStore = defineStore('tab', () => {
    const tabs = ref<TabItem[]>([
        { label: '仪表板', name: 'Dashboard', path: '/', closable: false }
    ])
    const activeTab = ref('Dashboard')

    const addTab = (tab: TabItem) => {
        const exists = tabs.value.find(t => t.name === tab.name)
        if (!exists) {
            tabs.value.push({ ...tab, closable: tab.closable ?? true })
        }
        activeTab.value = tab.name
    }

    const removeTab = (name: string) => {
        const index = tabs.value.findIndex(t => t.name === name)
        if (index === -1 || !tabs.value[index].closable) return

        tabs.value.splice(index, 1)

        // 如果关闭的是当前激活的 tab，则跳转到最后一个 tab
        if (activeTab.value === name) {
            const lastTab = tabs.value[tabs.value.length - 1]
            activeTab.value = lastTab.name
            return lastTab
        }
        return null
    }

    const closeOthers = (name: string) => {
        tabs.value = tabs.value.filter(t => !t.closable || t.name === name)
        activeTab.value = name
    }

    const closeAll = () => {
        tabs.value = tabs.value.filter(t => !t.closable)
        activeTab.value = tabs.value[0].name
    }

    return {
        tabs,
        activeTab,
        addTab,
        removeTab,
        closeOthers,
        closeAll
    }
})
