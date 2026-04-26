import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('user_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user_info') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  async function register(username, password, email) {
    await api.post('/api/auth/register', { username, password, email })
  }

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await api.post('/api/auth/login', formData)
    token.value = response.data.access_token
    localStorage.setItem('user_token', token.value)

    await fetchProfile()
  }

  async function fetchProfile() {
    const response = await api.get('/api/auth/profile')
    user.value = response.data
    localStorage.setItem('user_info', JSON.stringify(user.value))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('user_token')
    localStorage.removeItem('user_info')
  }

  return {
    token,
    user,
    isLoggedIn,
    register,
    login,
    fetchProfile,
    logout
  }
})
