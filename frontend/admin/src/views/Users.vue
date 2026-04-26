<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchUsers">
            <el-option label="全部" value="" />
            <el-option label="正常" value="active" />
            <el-option label="禁用" value="disabled" />
          </el-select>
        </div>
      </template>

      <el-table :data="users" v-loading="loading">
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column label="Peer状态" width="180">
          <template #default="{ row }">
            <div v-if="row.peer">
              <el-tag type="success" size="small">已配置</el-tag>
              <span class="peer-node">{{ row.peer.node_name }}</span>
            </div>
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
        <el-table-column label="操作" width="280">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button
              v-if="row.peer"
              size="small"
              type="danger"
              @click="deletePeer(row)"
            >
              删除Peer
            </el-button>
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
    </el-card>

    <el-dialog v-model="editDialogVisible" title="编辑用户" width="400px">
      <el-form :model="editForm" ref="editFormRef" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="editForm.password" type="password" placeholder="不修改请留空" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="updateUser" :loading="submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const submitting = ref(false)
const users = ref([])
const statusFilter = ref('')
const editDialogVisible = ref(false)
const editFormRef = ref()

const editForm = reactive({
  id: null,
  username: '',
  email: '',
  password: ''
})

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const { data } = await api.get('/api/users', { params })
    users.value = data
  } finally {
    loading.value = false
  }
}

function showEditDialog(user) {
  editForm.id = user.id
  editForm.username = user.username
  editForm.email = user.email
  editForm.password = ''
  editDialogVisible.value = true
}

async function updateUser() {
  submitting.value = true
  try {
    const payload = { email: editForm.email }
    if (editForm.password) {
      payload.password = editForm.password
    }
    await api.put(`/api/users/${editForm.id}`, payload)
    ElMessage.success('更新成功')
    editDialogVisible.value = false
    fetchUsers()
  } finally {
    submitting.value = false
  }
}

async function deletePeer(user) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 的Peer配置吗？\n这将同时从Agent删除配置，用户将无法继续使用VPN。`,
      '删除Peer确认',
      { type: 'warning' }
    )
    await api.delete(`/api/users/${user.id}/peer`)
    ElMessage.success('Peer配置已删除')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

async function toggleStatus(user) {
  const action = user.status === 'active' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${action}此用户吗? ${user.status === 'active' ? '禁用后将清除所有Peer配置' : ''}`,
      '确认',
      { type: 'warning' }
    )
    await api.post(`/api/users/${user.id}/${user.status === 'active' ? 'disable' : 'enable'}`)
    ElMessage.success(`${action}成功`)
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm('确定要删除此用户吗?', '确认', { type: 'warning' })
    await api.delete(`/api/users/${user.id}`)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

onMounted(fetchUsers)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.peer-node {
  margin-left: 8px;
  color: #606266;
  font-size: 12px;
}
</style>
