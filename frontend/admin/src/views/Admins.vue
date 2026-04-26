<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>管理员管理</span>
          <el-button type="primary" @click="showDialog()">
            <el-icon><Plus /></el-icon>
            添加管理员
          </el-button>
        </div>
      </template>

      <el-table :data="admins" v-loading="loading">
        <el-table-column prop="username" label="用户名" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'super_admin' ? 'danger' : 'primary'">
              {{ row.role === 'super_admin' ? '超级管理员' : '管理员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button
              size="small"
              @click="showDialog(row)"
              :disabled="row.role === 'super_admin'"
            >
              修改密码
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteAdmin(row)"
              :disabled="row.role === 'super_admin'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="editId ? '修改密码' : '添加管理员'" width="400px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="用户名" prop="username" v-if="!editId">
          <el-input v-model="form.username" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="用户名" v-else>
          <el-input v-model="form.username" disabled />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role" v-if="!editId">
          <el-select v-model="form.role">
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">确定</el-button>
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
const admins = ref([])
const dialogVisible = ref(false)
const editId = ref(null)
const formRef = ref()

const form = reactive({
  username: '',
  password: '',
  role: 'admin'
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

async function fetchAdmins() {
  loading.value = true
  try {
    const { data } = await api.get('/api/admins')
    admins.value = data
  } finally {
    loading.value = false
  }
}

function showDialog(admin = null) {
  editId.value = admin?.id || null
  form.username = admin?.username || ''
  form.password = ''
  form.role = 'admin'
  dialogVisible.value = true
}

async function submitForm() {
  try {
    await formRef.value.validate()
    submitting.value = true

    if (editId.value) {
      await api.put(`/api/admins/${editId.value}`, { password: form.password })
      ElMessage.success('密码已更新')
    } else {
      await api.post('/api/admins', form)
      ElMessage.success('添加成功')
    }

    dialogVisible.value = false
    fetchAdmins()
  } catch (error) {
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function deleteAdmin(admin) {
  try {
    await ElMessageBox.confirm('确定要删除此管理员吗?', '确认', { type: 'warning' })
    await api.delete(`/api/admins/${admin.id}`)
    ElMessage.success('删除成功')
    fetchAdmins()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

onMounted(fetchAdmins)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
