<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>注册审批</span>
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="fetchRegistrations">
            <el-option label="全部" value="" />
            <el-option label="待审批" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </div>
      </template>

      <el-table :data="registrations" v-loading="loading">
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type">
              {{ statusMap[row.status]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="reject_reason" label="拒绝原因">
          <template #default="{ row }">
            {{ row.reject_reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button size="small" type="success" @click="approve(row)">通过</el-button>
              <el-button size="small" type="danger" @click="showRejectDialog(row)">拒绝</el-button>
            </template>
            <span v-else class="text-muted">已处理</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="rejectDialogVisible" title="拒绝原因" width="400px">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="原因">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请输入拒绝原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="reject" :loading="submitting">确定拒绝</el-button>
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
const registrations = ref([])
const statusFilter = ref('pending')
const rejectDialogVisible = ref(false)

const rejectForm = reactive({
  id: null,
  reason: ''
})

const statusMap = {
  pending: { label: '待审批', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' }
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

async function fetchRegistrations() {
  loading.value = true
  try {
    const params = statusFilter.value ? { status: statusFilter.value } : {}
    const { data } = await api.get('/api/registrations', { params })
    registrations.value = data
  } finally {
    loading.value = false
  }
}

async function approve(reg) {
  try {
    await ElMessageBox.confirm('确定通过此注册申请吗?', '确认', { type: 'info' })
    await api.post(`/api/registrations/${reg.id}/approve`)
    ElMessage.success('已通过')
    fetchRegistrations()
  } catch (error) {
    if (error !== 'cancel') console.error(error)
  }
}

function showRejectDialog(reg) {
  rejectForm.id = reg.id
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

async function reject() {
  if (!rejectForm.reason.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }

  submitting.value = true
  try {
    await api.post(`/api/registrations/${rejectForm.id}/reject`, { reason: rejectForm.reason })
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    fetchRegistrations()
  } finally {
    submitting.value = false
  }
}

onMounted(fetchRegistrations)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-muted {
  color: #909399;
}
</style>
