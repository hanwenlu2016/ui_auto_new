import axios from 'axios'
import { createDiscreteApi } from 'naive-ui'

const { message } = createDiscreteApi(['message'])

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      if (status === 401) {
        message.error('Session expired, please login again')
        localStorage.removeItem('token')
        window.location.href = '/login'
      } else {
        message.error(data.detail || 'An error occurred')
      }
    } else {
      message.error('Network error')
    }
    return Promise.reject(error)
  }
)

export default api
