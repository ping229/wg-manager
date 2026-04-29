<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="left-actions">
            <el-select v-model="selectedPortalSite" placeholder="选择Portal站点" @change="handlePortalChange" style="width: 200px;">
              <el-option v-for="site in portalSites" :key="site.id" :label="site.name" :value="site.id" />
            </el-select>
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="handleFilterChange" style="width: 120px;">
              <el-option label="全部" value="" />
              <el-option label="正常" value="active" />
              <el-option label="禁用" value="disabled" />
            </el-select>
          </div>
          <div class="right-actions">
            <el-button type="success" :disabled="selectedRows.length === 0" @click="batchEnable">
              批量启用 ({{ selectedRows.length }})
            </el-button>
            <el-button type="warning" :disabled="selectedRows.length === 0" @click="batchDisable">
              批量禁用 ({{ selectedRows.length }})
            </el-button>
            <el-button type="primary" @click="showCreateDialog" :disabled="!selectedPortalSite">
              <el-icon><Plus /></el-icon>
              创建用户
            </el-button>
            <el-button @click="showBatchImportDialog" :disabled="!selectedPortalSite">
              <el-icon><Upload /></el-icon>
              批量导入
            </el-button>
            <el-button @click="exportUsers" :disabled="users.length === 0">
              <el-icon><Download /></el-icon>
              导出用户
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        :data="paginatedData"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        ref="tableRef"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column label="密码" width="150">
          <template #default="{ row }">
            <div class="password-cell">
              <span v-if="row._showPassword">{{ row.password || '-' }}</span>
              <span v-else>******</span>
              <el-button size="small" text @click="togglePassword(row)">
                {{ row._showPassword ? '隐藏' : '显示' }}
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="Portal站点" width="120">
          <template #default="{ row }">
            {{ row.portal_site_name }}
          </template>
        </el-table-column>
        <el-table-column label="Peer状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.peer" type="success" size="small">已配置</el-tag>
            <el-tag v-else type="info" size="small">未配置</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="showPasswordDialog(row)">改密</el-button>
            <el-button
              size="small"
              :type="row.status === 'active' ? 'warning' : 'success'"
              @click="toggleStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
            <el-button size="small" type="danger" @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="users.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 创建用户对话框 -->
    <el-dialog v-model="createDialogVisible" title="创建用户" width="400px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="用户名（唯一）" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="createForm.email" placeholder="邮箱地址" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="createForm.password" type="password" placeholder="登录密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createUser" :loading="submitting">创建</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="batchImportDialogVisible" title="批量导入用户" width="600px">
      <div class="batch-import-tips">
        <p>请上传 CSV 或 TXT 文件，每行一个用户，格式：用户名,密码,邮箱</p>
        <p>示例：</p>
        <pre>user1,pass123,user1@example.com
user2,pass456,user2@example.com</pre>
      </div>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".csv,.txt"
        :on-change="handleFileChange"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处，或 <em>点击上传</em></div>
      </el-upload>
      <div v-if="parsedUsers.length > 0" class="parsed-users">
        <h4>已解析 {{ parsedUsers.length }} 个用户</h4>
        <el-table :data="parsedUsers" max-height="200">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="email" label="邮箱" />
          <el-table-column label="状态">
            <template #default="{ row }">
              <el-tag v-if="row.valid" type="success">有效</el-tag>
              <el-tag v-else type="danger">{{ row.error }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="batchImportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="batchImport" :loading="submitting" :disabled="validUsers.length === 0">
          导入 {{ validUsers.length }} 个用户
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
      <el-form :model="passwordForm" ref="passwordFormRef" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="passwordForm.username" disabled />
        </el-form-item>
        <el-form-item label="当前密码">
          <el-input v-model="passwordForm.currentPassword" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="passwordForm.newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updatePassword" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, UploadFilled } from '@element-plus/icons-vue'
import { api } from '../api'

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const portalSites = ref([])
const selectedPortalSite = ref(null)
const statusFilter = ref('')
const createDialogVisible = ref(false)
const batchImportDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const createFormRef = ref()
const uploadRef = ref()
const parsedUsers = ref([])
const selectedRows = ref([])
const tableRef = ref()

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

const createForm = reactive({
  username: '',
  email: '',
  password: ''
})

const passwordForm = reactive({
  portal_site_id: null,
  user_id: null,
  username: '',
  currentPassword: '',
  newPassword: ''
})

const createRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const validUsers = computed(() => parsedUsers.value.filter(u => u.valid))

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return users.value.slice(start, end)
})

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function handlePortalChange() {
  currentPage.value = 1
  selectedRows.value = []
  fetchUsers()
}

function handleFilterChange() {
  currentPage.value = 1
  fetchUsers()
}

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 页码改变时自动更新 paginatedData
}

async function fetchPortalSites() {
  try {
    const { data } = await api.get('/api/portal-sites')
    portalSites.value = data
    if (data.length > 0 && !selectedPortalSite.value) {
      selectedPortalSite.value = data[0].id
      fetchUsers()
    }
  } catch (error) {
    console.error('Failed to fetch portal sites:', error)
  }
}

async function fetchUsers() {
  if (!selectedPortalSite.value) {
    users.value = []
    return
  }
  loading.value = true
  try {
    const params = { portal_site_id: selectedPortalSite.value }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const { data } = await api.get('/api/users', { params })
    users.value = data.map(u => ({ ...u, _showPassword: false }))
  } finally {
    loading.value = false
  }
}

function togglePassword(user) {
  user._showPassword = !user._showPassword
}

function showCreateDialog() {
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createDialogVisible.value = true
}

async function createUser() {
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    await api.post('/api/users/create', {
      portal_site_id: selectedPortalSite.value,
      username: createForm.username,
      email: createForm.email,
      password: createForm.password
    })
    ElMessage.success('用户创建成功')
    createDialogVisible.value = false
    fetchUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

function showBatchImportDialog() {
  parsedUsers.value = []
  batchImportDialogVisible.value = true
}

function handleFileChange(file) {
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target.result
    const lines = content.split('\n').filter(line => line.trim())
    parsedUsers.value = lines.map(line => {
      const parts = line.trim().split(',')
      if (parts.length >= 3) {
        return {
          username: parts[0].trim(),
          password: parts[1].trim(),
          email: parts[2].trim(),
          valid: parts[0].trim() && parts[1].trim() && parts[2].trim()
        }
      }
      return {
        username: parts[0] || '',
        password: parts[1] || '',
        email: parts[2] || '',
        valid: false,
        error: '格式错误'
      }
    })
  }
  reader.readAsText(file.raw)
}

async function batchImport() {
  submitting.value = true
  try {
    const usersToImport = validUsers.value.map(u => ({
      username: u.username,
      password: u.password,
      email: u.email
    }))
    const { data } = await api.post('/api/users/batch-create', {
      portal_site_id: selectedPortalSite.value,
      users: usersToImport
    })
    ElMessage.success(data.message)
    batchImportDialogVisible.value = false
    fetchUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '导入失败')
  } finally {
    submitting.value = false
  }
}

function showPasswordDialog(user) {
  passwordForm.portal_site_id = user.portal_site_id
  passwordForm.user_id = user.id
  passwordForm.username = user.username
  passwordForm.currentPassword = user.password
  passwordForm.newPassword = ''
  passwordDialogVisible.value = true
}

async function updatePassword() {
  if (!passwordForm.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }

  submitting.value = true
  try {
    await api.put(`/api/users/${passwordForm.portal_site_id}/${passwordForm.user_id}/password`, {
      password: passwordForm.newPassword
    })
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
    fetchUsers()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '修改失败')
  } finally {
    submitting.value = false
  }
}

function exportUsers() {
  if (users.value.length === 0) {
    ElMessage.warning('没有用户数据可导出')
    return
  }

  const headers = ['用户名', '密码', '邮箱', '状态', 'Portal站点', '注册时间']
  const rows = users.value.map(u => [
    u.username,
    u.password || '',
    u.email,
    u.status,
    u.portal_site_name,
    formatDate(u.created_at)
  ])

  const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n')
  const blob = new Blob(['﻿' + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `users_${selectedPortalSite.value}_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  window.URL.revokeObjectURL(url)

  ElMessage.success(`已导出 ${users.value.length} 个用户`)
}

async function toggleStatus(user) {
  const action = user.status === 'active' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}此用户吗? ${user.status === 'active' ? '禁用后将清除所有Peer配置' : ''}`,
      '确认',
      { type: 'warning' }
    )
    await api.post(`/api/users/${user.portal_site_id}/${user.id}/${user.status === 'active' ? 'disable' : 'enable'}`)
    ElMessage.success(`${action}成功`)
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

async function batchEnable() {
  try {
    await ElMessageBox.confirm(`确定要启用选中的 ${selectedRows.value.length} 个用户吗?`, '批量启用', { type: 'info' })

    let success = 0
    let failed = 0

    for (const row of selectedRows.value) {
      try {
        await api.post(`/api/users/${row.portal_site_id}/${row.id}/enable`)
        success++
      } catch {
        failed++
      }
    }

    if (success > 0) {
      ElMessage.success(`成功启用 ${success} 个用户${failed > 0 ? `，失败 ${failed} 个` : ''}`)
    } else {
      ElMessage.error('批量启用失败')
    }

    selectedRows.value = []
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function batchDisable() {
  try {
    await ElMessageBox.confirm(
      `确定要禁用选中的 ${selectedRows.value.length} 个用户吗? 禁用后将清除所有Peer配置`,
      '批量禁用',
      { type: 'warning' }
    )

    let success = 0
    let failed = 0

    for (const row of selectedRows.value) {
      try {
        await api.post(`/api/users/${row.portal_site_id}/${row.id}/disable`)
        success++
      } catch {
        failed++
      }
    }

    if (success > 0) {
      ElMessage.success(`成功禁用 ${success} 个用户${failed > 0 ? `，失败 ${failed} 个` : ''}`)
    } else {
      ElMessage.error('批量禁用失败')
    }

    selectedRows.value = []
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm('确定要删除此用户吗?', '确认', { type: 'warning' })
    await api.delete(`/api/users/${user.portal_site_id}/${user.id}`)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(() => {
  fetchPortalSites()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left-actions, .right-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.password-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.batch-import-tips {
  margin-bottom: 20px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.batch-import-tips p {
  margin: 5px 0;
  color: #606266;
}

.batch-import-tips pre {
  background: #fff;
  padding: 10px;
  border-radius: 4px;
  font-size: 12px;
}

.parsed-users {
  margin-top: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
