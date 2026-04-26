import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('admin_token') || '')
  const admin = ref(JSON.parse(localStorage.getItem('admin_info') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isSuperAdmin = computed(() => admin.value?.role === 'super_admin')

  async function login(username, password) {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)

    const response = await api.post('/api/auth/login', formData)
    token.value = response.data.access_token
    localStorage.setItem('admin_token', token.value)

    await fetchProfile()
  }

  async function fetchProfile() {
    const response = await api.get('/api/auth/profile')
    admin.value = response.data
    localStorage.setItem('admin_info', JSON.stringify(admin.value))
  }

  function logout() {
    token.value = ''
    admin.value = null
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_info')
  }

  return {
    token,
    admin,
    isLoggedIn,
    isSuperAdmin,
    login,
    fetchProfile,
    logout
  }
})
