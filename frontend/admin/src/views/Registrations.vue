<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>注册审批</span>
          <div class="header-actions">
            <el-button type="success" :disabled="selectedRows.length === 0" @click="batchApprove">
              批量通过 ({{ selectedRows.length }})
            </el-button>
            <el-button type="danger" :disabled="selectedRows.length === 0" @click="showBatchRejectDialog">
              批量拒绝 ({{ selectedRows.length }})
            </el-button>
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable @change="handleFilterChange" style="width: 120px;">
              <el-option label="全部" value="" />
              <el-option label="待审批" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
          </div>
        </div>
      </template>

      <el-table
        :data="paginatedData"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        ref="tableRef"
      >
        <el-table-column type="selection" width="50" :selectable="canSelect" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusMap[row.status]?.type">
              {{ statusMap[row.status]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="portal_site_name" label="Portal站点" width="120" />
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

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="registrations.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 单个拒绝对话框 -->
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

    <!-- 批量拒绝对话框 -->
    <el-dialog v-model="batchRejectDialogVisible" title="批量拒绝" width="400px">
      <p>将拒绝 {{ selectedRows.length }} 个注册申请</p>
      <el-form label-width="80px">
        <el-form-item label="拒绝原因">
          <el-input v-model="batchRejectReason" type="textarea" :rows="3" placeholder="请输入拒绝原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchRejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="batchReject" :loading="submitting">确定拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api'

const loading = ref(false)
const submitting = ref(false)
const registrations = ref([])
const statusFilter = ref('pending')
const rejectDialogVisible = ref(false)
const batchRejectDialogVisible = ref(false)
const selectedRows = ref([])
const batchRejectReason = ref('')
const tableRef = ref()

// 分页
const currentPage = ref(1)
const pageSize = ref(10)

const rejectForm = reactive({
  portal_site_id: null,
  id: null,
  reason: ''
})

const statusMap = {
  pending: { label: '待审批', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' }
}

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return registrations.value.slice(start, end)
})

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

function canSelect(row) {
  return row.status === 'pending'
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function handleFilterChange() {
  currentPage.value = 1
  fetchRegistrations()
}

function handleSizeChange() {
  currentPage.value = 1
}

function handleCurrentChange() {
  // 页码改变时自动更新 paginatedData
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
    await api.post(`/api/registrations/${reg.portal_site_id}/${reg.id}/approve`)
    ElMessage.success('已通过')
    fetchRegistrations()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

function showRejectDialog(reg) {
  rejectForm.portal_site_id = reg.portal_site_id
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
    await api.post(`/api/registrations/${rejectForm.portal_site_id}/${rejectForm.id}/reject`, { reason: rejectForm.reason })
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    fetchRegistrations()
  } catch (error) {
    ElMessage.error('操作失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

function showBatchRejectDialog() {
  batchRejectReason.value = ''
  batchRejectDialogVisible.value = true
}

async function batchApprove() {
  try {
    await ElMessageBox.confirm(`确定通过选中的 ${selectedRows.value.length} 个注册申请吗?`, '批量通过', { type: 'info' })

    let success = 0
    let failed = 0

    for (const row of selectedRows.value) {
      try {
        await api.post(`/api/registrations/${row.portal_site_id}/${row.id}/approve`)
        success++
      } catch {
        failed++
      }
    }

    if (success > 0) {
      ElMessage.success(`成功通过 ${success} 个申请${failed > 0 ? `，失败 ${failed} 个` : ''}`)
    } else {
      ElMessage.error('批量通过失败')
    }

    selectedRows.value = []
    fetchRegistrations()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function batchReject() {
  if (!batchRejectReason.value.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }

  submitting.value = true
  try {
    let success = 0
    let failed = 0

    for (const row of selectedRows.value) {
      try {
        await api.post(`/api/registrations/${row.portal_site_id}/${row.id}/reject`, { reason: batchRejectReason.value })
        success++
      } catch {
        failed++
      }
    }

    if (success > 0) {
      ElMessage.success(`成功拒绝 ${success} 个申请${failed > 0 ? `，失败 ${failed} 个` : ''}`)
    } else {
      ElMessage.error('批量拒绝失败')
    }

    batchRejectDialogVisible.value = false
    selectedRows.value = []
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

.header-actions {
  display: flex;
  gap: 10px;
}

.text-muted {
  color: #909399;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
