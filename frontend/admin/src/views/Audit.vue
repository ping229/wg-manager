<template>
  <div class="page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <div class="filters">
            <el-select v-model="filters.action" placeholder="操作类型" clearable style="width: 120px; margin-right: 10px;">
              <el-option label="全部" value="" />
              <el-option label="创建" value="create" />
              <el-option label="更新" value="update" />
              <el-option label="删除" value="delete" />
              <el-option label="登录" value="login" />
            </el-select>
            <el-date-picker
              v-model="filters.date"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              @change="fetchLogs"
            />
          </div>
        </div>
      </template>

      <el-table :data="logs" v-loading="loading">
        <el-table-column prop="admin_username" label="操作人" width="120" />
        <el-table-column prop="action" label="操作" width="80">
          <template #default="{ row }">
            <el-tag :type="actionMap[row.action]?.type" size="small">
              {{ actionMap[row.action]?.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源类型" width="100" />
        <el-table-column prop="resource_id" label="资源ID" width="80" />
        <el-table-column prop="detail" label="详情" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="130" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.size"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchLogs"
        @current-change="fetchLogs"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { api } from '../api'

const loading = ref(false)
const logs = ref([])

const filters = reactive({
  action: '',
  date: null
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0
})

const actionMap = {
  create: { label: '创建', type: 'success' },
  update: { label: '更新', type: 'primary' },
  delete: { label: '删除', type: 'danger' },
  login: { label: '登录', type: 'info' }
}

function formatDate(date) {
  if (!date) return ''
  return new Date(date).toLocaleString('zh-CN')
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.size,
      limit: pagination.size
    }
    if (filters.action) {
      params.action = filters.action
    }
    if (filters.date && filters.date.length === 2) {
      params.start_date = filters.date[0].toISOString()
      params.end_date = filters.date[1].toISOString()
    }

    const { data } = await api.get('/api/audit', { params })
    logs.value = data.items
    pagination.total = data.total
  } finally {
    loading.value = false
  }
}

onMounted(fetchLogs)
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  align-items: center;
}
</style>
