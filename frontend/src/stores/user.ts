import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/api'
import { useRouter } from 'vue-router'

export const useUserStore = defineStore('user', () => {
    const token = ref(localStorage.getItem('token') || '')
    const user = ref<any>(null)
    const router = useRouter()

    const login = async (credentials: any) => {
        const params = new URLSearchParams()
        params.append('username', credentials.email)
        params.append('password', credentials.password)

        const response = await api.post('/login/access-token', params, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })

        token.value = response.data.access_token
        localStorage.setItem('token', token.value)
        await fetchUser()
    }

    const fetchUser = async () => {
        if (!token.value) return
        try {
            const response = await api.get('/users/me')
            user.value = response.data
        } catch (error) {
            logout()
        }
    }

    const logout = () => {
        token.value = ''
        user.value = null
        localStorage.removeItem('token')
        router.push('/login')
    }

    return {
        token,
        user,
        login,
        fetchUser,
        logout
    }
})
